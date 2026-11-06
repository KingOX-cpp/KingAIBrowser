import { KingAI, BrowserSession, KingAIError } from './client.mjs';
import { captureState, observeOperation, previewExpression } from './observation.mjs';

const changesPage = new Set(['go_to_url','open_tab','switch_tab','close_tab','go_back','refresh','click_element',
  'input_text','scroll_down','scroll_up','scroll_to_text','send_keys','select_dropdown_option','web_search']);

export class BrowserAutomation {
  constructor({ profile_id, session_id, headless = false, ...options } = {}) {
    this.client = new KingAI(options); this.browser = undefined; this.connectionFailed = false;
    this.profileId = profile_id; this.sessionId = session_id; this.headless = headless;
  }
  async _browser() {
    if (this.connectionFailed) throw new KingAIError({ code:'KINGAI_CONNECTION_UNCERTAIN',message:'Inspect session/request state before explicitly recovering; do not replay side effects.' });
    if (!this.browser) {
      try { this.browser = this.sessionId ? await this.client.attach(this.sessionId)
        : await this.client.start({ ...(this.profileId ? {profile_id:this.profileId}:{}), headless:this.headless }); }
      catch(error) { this.connectionFailed=true; throw error; }
    }
    return this.browser;
  }
  describeError(error) {
    const code=error.code || 'KINGAI_ACTION_FAILED';
    if (['OUTCOME_UNKNOWN','MCP_DISCONNECTED','INVALID_TOOL_RESPONSE'].includes(code)) this.connectionFailed=true;
    return {code,message:error.message,details:error.details,
      hint:code==='RESULT_TOO_LARGE'?'Explicitly page read-only results; never replay a side-effecting expression.':'Inspect session/request status before repeating side effects.'};
  }
  execute(action, args={}) {
    return this.client.exclusive(async()=>{
      try {
        const result=await this._dispatch(action,args);
        return changesPage.has(action) ? observeOperation(await this._browser(),action,result) : result;
      } catch(error) { this.describeError(error); throw error; }
    });
  }
  async _dispatch(action, args) {
    const {url,ref,selector,target_id,text,query,goal,keys,scroll_amount,tool_name,arguments:params={}}=args;
    if (args.index!==undefined || args.tab_id!==undefined) throw new TypeError('Use observed ref/target_id, not legacy numeric indices');
    if(action==='tools') return this.client.tools();
    if(action==='profiles') return this.client.profiles();
    if(action==='wait') {
      const seconds=args.seconds ?? 3;
      if(!Number.isFinite(seconds)||seconds<0||seconds>120)throw new TypeError('seconds must be between 0 and 120');
      await new Promise(resolve=>setTimeout(resolve,seconds*1000));return {waitedSeconds:seconds};
    }
    if(action==='mcp_call') {
      if(!tool_name)throw new TypeError('tool_name is required');
      const data={...params};
      if(/^(browser_|tabs_|cookies_|storage_|network_|console_)/.test(tool_name)&&!['browser_start','browser_sessions_list','browser_attach'].includes(tool_name))data.session_id=(await this._browser()).sessionId;
      if(tool_name==='browser_evaluate')data.expression=previewExpression(data.expression,data.await_promise!==false);
      const result=await this.client.call(tool_name,data);
      if(['browser_start','browser_attach'].includes(tool_name)){
        this.browser=new BrowserSession(this.client,result.sessionId||data.session_id,result);this.connectionFailed=false;
      } else if(['browser_close','browser_detach'].includes(tool_name)){this.browser=undefined;this.connectionFailed=true;}
      return result;
    }
    const browser=await this._browser();
    if(action==='go_to_url'||action==='open_tab') {
      if(!url)throw new TypeError('url is required');
      return action==='go_to_url'?browser.goto(url):browser.newTab(url);
    }
    if(action==='switch_tab'||action==='close_tab') {
      if(!target_id)throw new TypeError('target_id is required');
      return action==='switch_tab'?browser.activateTab(target_id):browser.closeTab(target_id);
    }
    if(action==='web_search') {
      if(!query)throw new TypeError('query is required');return browser.goto('https://www.google.com/search?q='+encodeURIComponent(query));
    }
    if(action==='go_back'||action==='refresh')return browser.evaluate(action==='go_back'?'history.back()':'location.reload()');
    if(action==='snapshot'||action==='query')return browser.call('browser_'+action,params);
    if(action==='extract_content')return {goal,page:await browser.read({max_chars:20000})};
    if(action==='scroll_up'||action==='scroll_down')return browser.scroll(Math.abs(scroll_amount??700)*(action==='scroll_up'?-1:1));
    if(action==='send_keys') {
      if(!keys)throw new TypeError('keys is required');
      const parts=keys.split('+'),key=parts.pop(),aliases={CTRL:'Control',CONTROL:'Control',ALT:'Alt',SHIFT:'Shift',META:'Meta',CMD:'Meta'};
      const modifiers=parts.map(p=>{if(!aliases[p.toUpperCase()])throw new TypeError('Unknown modifier');return aliases[p.toUpperCase()];});
      return browser.key(key,{modifiers});
    }
    if(action==='scroll_to_text') {
      if(!text)throw new TypeError('text is required');
      return browser.evaluate(`(()=>{const q=${JSON.stringify(text)},w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n,count=0;
        while((n=w.nextNode())&&count++<20000){if(n.textContent.includes(q)){n.parentElement.scrollIntoView({block:'center'});return {found:true};}}return {found:false};})()`);
    }
    if((!ref&&!selector)||(ref&&selector))throw new TypeError('Provide exactly one observed ref or selector');
    const target=ref?{ref}:{selector};
    if(action==='click_element')return browser.call('browser_click',target);
    if(action==='input_text') {if(text===undefined)throw new TypeError('text is required');return browser.call('browser_fill',{...target,text});}
    if(action==='select_dropdown_option') {if(text===undefined)throw new TypeError('text is required');return browser.call('browser_select',{...target,values:[text],match_by:'label'});}
    if(action==='get_dropdown_options') {
      if(!selector)throw new TypeError('A precise select selector is required; use query for ref children');
      return browser.evaluatePreview(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.tagName!=='SELECT')throw new Error('SELECT_NOT_FOUND');return Array.from(e.options,o=>({label:o.label,value:o.value,selected:o.selected}));})()`);
    }
    throw new TypeError('Unknown action: '+action);
  }
  getCurrentState() {
    return this.client.exclusive(()=>{
      if(!this.browser)throw new Error('Browser not started; use go_to_url/open_tab first');
      return captureState(this.browser);
    });
  }
  async close(){await this.client.close();this.browser=undefined;this.connectionFailed=true;}
}
