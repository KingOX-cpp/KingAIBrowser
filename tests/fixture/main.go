// TEST ONLY. A deterministic stdio MCP fixture. Never launches a real browser.
package main

import("bufio";"encoding/json";"fmt";"os";"strings";"time")

type obj=map[string]any
func main(){
 profiles:=map[string]obj{"default": {"id":"default","name":"默认环境"}}
 sessions:=map[string]string{};tabs:=[]obj{};url:="about:blank";trace:=[]string{};failNext:="";next:=0
 scanner:=bufio.NewScanner(os.Stdin);scanner.Buffer(make([]byte,4096),32*1024*1024)
 write:=func(v any){b,_:=json.Marshal(v);fmt.Println(string(b))}
 for scanner.Scan(){var req obj;if json.Unmarshal(scanner.Bytes(),&req)!=nil{continue};id,hasID:=req["id"];if !hasID{continue}
  method,_:=req["method"].(string);p,_:=req["params"].(map[string]any);var result any
  switch method {
  case "initialize": result=obj{"protocolVersion":"2025-11-25","capabilities":obj{"tools":obj{}},"serverInfo":obj{"name":"kingai-test-fixture","version":"0.3.0"}}
  case "tools/list":result=obj{"tools":[]obj{{"name":"sdk_info","inputSchema":obj{"type":"object"}},{"name":"profiles_list","inputSchema":obj{"type":"object"}}}}
  case "tools/call":
   name,_:=p["name"].(string);a,_:=p["arguments"].(map[string]any);if a==nil{a=obj{}};trace=append(trace,name)
   var value any;code:="";profileID,_:=a["profile_id"].(string)
   if name=="fixture_fail_next"{failNext,_=a["code"].(string);value=obj{"armed":true}
   }else if failNext!=""{code=failNext;failNext=""
   }else{switch name {
   case "sdk_info":value=obj{"sdkApiVersion":1,"fixture":true}
   case "profiles_list":list:=[]obj{};for _,v:=range profiles{list=append(list,v)};value=obj{"profiles":list}
   case "profiles_create":duplicate:=false;for _,v:=range profiles{if v["name"]==a["name"]{duplicate=true}}
    if duplicate{code="PROFILE_NAME_EXISTS"}else{next++;profileID=fmt.Sprintf("profile-%d",next);profiles[profileID]=obj{"id":profileID,"name":a["name"]};value=obj{"profileId":profileID}}
   case "profiles_get":if v,ok:=profiles[profileID];ok{value=v}else{code="PROFILE_NOT_FOUND"}
   case "profiles_update":if _,ok:=profiles[profileID];!ok{code="PROFILE_NOT_FOUND"}else{busy:=false;for _,v:=range sessions{if v==profileID{busy=true}};if busy{code="SESSION_BUSY"}else{if n,ok:=a["name"];ok{profiles[profileID]["name"]=n};value=obj{"updated":true,"profileId":profileID}}}
   case "profiles_delete":if a["confirm"]!=true{code="CONFIRMATION_REQUIRED"}else if len(profiles)<=1{code="LAST_PROFILE"}else{delete(profiles,profileID);value=obj{"deleted":true}}
   case "browser_start":if profileID==""{profileID="default"};if _,ok:=profiles[profileID];!ok{code="PROFILE_NOT_FOUND"}else{sid:="session-"+profileID;sessions[sid]=profileID;tabs=[]obj{{"id":"tab-1","targetId":"tab-1","url":"about:blank"}};value=obj{"sessionId":sid}}
   case "browser_attach":sid,_:=a["session_id"].(string);if _,ok:=sessions[sid];!ok{code="SESSION_NOT_FOUND"}else{value=obj{"sessionId":sid}}
   case "browser_detach":value=obj{"detached":true}
   case "browser_close":sid,_:=a["session_id"].(string);delete(sessions,sid);value=obj{"closed":true}
   case "tabs_new":u,_:=a["url"].(string);if u==""{u="about:blank"};url=u;tid:=fmt.Sprintf("tab-%d",len(tabs)+1);tabs=append(tabs,obj{"id":tid,"targetId":tid,"url":u});value=obj{"targetId":tid}
   case "tabs_list":value=obj{"tabs":tabs}
   case "tabs_activate","tabs_close":value=obj{"targetId":a["target_id"]}
   case "browser_navigate":url,_=a["url"].(string);value=obj{"url":url}
   case "browser_read":value=obj{"url":url,"title":"Example Domain","text":"Example fixture page"}
   case "browser_snapshot","browser_query":value=obj{"nodes":[]obj{{"ref":"e1","role":"link","name":"More information"}}}
   case "browser_click","browser_fill","browser_scroll","browser_key":value=obj{"actionDispatched":true,"humanizeRequested":true,"humanizationRequiresEntitlement":true}
   case "browser_evaluate":expr,_:=a["expression"].(string);if strings.Contains(expr,"const source"){value=obj{"value":obj{"title":"Example Domain"},"truncated":false}}else{value="Example Domain"}
   case "fixture_trace":value=trace
   case "fixture_delay":time.Sleep(150*time.Millisecond);value=obj{"done":true}
   case "fixture_bad_response":result=obj{"content":[]obj{{"type":"text","text":"not JSON"}}}
   default:code="TOOL_NOT_FOUND"
   }}
   if result==nil{envelope:=obj{"ok":true,"result":value};if code!=""{envelope=obj{"ok":false,"code":code,"message":"fixture error: "+code}};b,_:=json.Marshal(envelope);result=obj{"content":[]obj{{"type":"text","text":string(b)}}}}
  default:write(obj{"jsonrpc":"2.0","id":id,"error":obj{"code":-32601,"message":"unknown method"}});continue
  }
  write(obj{"jsonrpc":"2.0","id":id,"result":result})
 }
}
