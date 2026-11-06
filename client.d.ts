export type Arguments = Record<string, unknown>;
export interface Options {
  mcpExecutable?: string; timeoutMs?: number; language?: string;
  fileRoots?: string[]; downloadDir?: string; artifactDir?: string;
}
export interface Tool { name: string; description?: string; inputSchema: Arguments }
export interface StartOptions { profile_id?: string; headless?: boolean; temporary?: boolean }
export interface UpdateOptions { name?: string; group_name?: string; patch?: Arguments }
export interface InputOptions extends Arguments { ref?: string; frame_id?: string; humanize?: boolean; observe?: boolean }
export interface Observation { operationStatus: string; operationResult: unknown; businessOutcome: 'not_verified'; observationStatus: 'captured'|'unavailable'; observation?: Arguments; observationError?: Arguments }
export class KingAIError extends Error { code: string; details: Arguments; constructor(details: Arguments) }
export function discoverMcp(executable?: string): Promise<string>;
export class KingAI {
  constructor(options?: Options);
  serverInfo?: Arguments;
  connect(): Promise<this>; close(): Promise<void>;
  exclusive<T>(work: (api: this) => Promise<T>): Promise<T>;
  call<T=unknown>(name: string, args?: Arguments): Promise<T>;
  tools(): Promise<Tool[]>; info(): Promise<Arguments>; profiles(): Promise<Arguments>;
  profile(profileId: string): Promise<Arguments>;
  createProfile(name: string, options?: {group_name?:string; language?:string}): Promise<{profileId:string}>;
  updateProfile(profileId: string, options?: UpdateOptions): Promise<Arguments>;
  deleteProfile(profileId: string, options?: {confirm?:boolean}): Promise<Arguments>;
  sessions(): Promise<Arguments>; start(options?: StartOptions): Promise<BrowserSession>;
  attach(sessionId: string): Promise<BrowserSession>; requestStatus(requestId: string): Promise<Arguments>;
  skills(): Promise<unknown>; describeSkill(skillId:string): Promise<unknown>;
  runSkill(profileId:string,skillId:string,options?:Arguments):Promise<unknown>;
  skillStatus(runId:string):Promise<unknown>; cancelSkill(runId:string):Promise<unknown>; skillRuns():Promise<unknown>;
}
export class BrowserSession {
  constructor(client:KingAI,sessionId:string,info?:Arguments);
  client:KingAI; sessionId:string; info:Arguments;
  call<T=unknown>(name:string,args?:Arguments & {observe?:boolean}):Promise<T>;
  tabs():Promise<unknown>; newTab(url?:string):Promise<unknown>;
  activateTab(targetId:string):Promise<unknown>; closeTab(targetId:string):Promise<unknown>;
  goto(url:string):Promise<unknown>; read(options?:Arguments):Promise<Arguments>;
  snapshot(options?:Arguments):Promise<Arguments>; query(options?:Arguments):Promise<Arguments>;
  click(selector?:string,options?:InputOptions):Promise<unknown>;
  fill(selector:string|undefined,text:string,options?:InputOptions):Promise<unknown>;
  type(selector:string|undefined,text:string,options?:InputOptions):Promise<unknown>;
  evaluate(expression:string,options?:Arguments):Promise<unknown>;
  evaluatePreview(expression:string,options?:Arguments):Promise<unknown>;
  wait(options?:Arguments):Promise<unknown>; screenshot(options?:Arguments):Promise<unknown>;
  scroll(deltaY:number,options?:InputOptions):Promise<unknown>; key(key:string,options?:Arguments):Promise<unknown>;
  hover(selector?:string,options?:InputOptions):Promise<unknown>;
  pdf(options?:Arguments):Promise<unknown>; cookies():Promise<unknown>; storage(options?:Arguments):Promise<unknown>;
  upload(paths:string[],selector?:string,options?:Arguments):Promise<unknown>;
  download(selector?:string,options?:Arguments):Promise<unknown>; detach():Promise<unknown>; close():Promise<unknown>;
}
export class BrowserAutomation {
  constructor(options?:Options & {profile_id?:string;session_id?:string;headless?:boolean});
  client:KingAI; browser?:BrowserSession;
  execute(action:string,args?:Arguments):Promise<unknown>;
  getCurrentState():Promise<Arguments>; describeError(error:Error):Arguments; close():Promise<void>;
}
