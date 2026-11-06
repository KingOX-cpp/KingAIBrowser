// Package kingai calls the installed KingAI MCP; browser secrets stay in Runtime.
package kingai

import (
 "bytes"
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "strings"
 "sync"
 "time"

 "github.com/modelcontextprotocol/go-sdk/mcp"
)

type Arguments = map[string]any
type Options struct {
 MCPExecutable string
 Timeout time.Duration
 Language string
 FileRoots []string
 DownloadDir string
 ArtifactDir string
}
type Error struct { Code string; Message string; Details Arguments; OutcomeUnknown bool }
func (e *Error) Error() string { return e.Code+": "+e.Message }

// Discover never searches PATH, scans disks, downloads or launches a browser.
func Discover(explicit string) (string,error) {
 path:=explicit
 if path=="" { path=os.Getenv("KINGAI_MCP_EXECUTABLE") }
 if path=="" {
  home,err:=os.UserHomeDir();if err!=nil{return "",err}
  root:=filepath.Join(home,".config","KingAIBrowser")
  if runtime.GOOS=="windows" { local:=os.Getenv("LOCALAPPDATA");if local==""{return "",&Error{Code:"MCP_NOT_FOUND",Message:"LOCALAPPDATA missing; specify MCPExecutable"}};root=filepath.Join(local,"KingAIBrowser") }
  if runtime.GOOS=="darwin" { root=filepath.Join(home,"Library","Application Support","KingAIBrowser") }
  file,err:=os.Open(filepath.Join(root,"sdk-installation.json"))
  if err!=nil{return "",&Error{Code:"MCP_NOT_FOUND",Message:"Open Manager once or specify MCPExecutable"}}
  defer file.Close()
  var record struct { SchemaVersion int `json:"schemaVersion"`; MCPExecutable string `json:"mcpExecutable"` }
  // The discovery file contains only a location hint, never credentials.
  buf,readErr:=io.ReadAll(io.LimitReader(file,65537));n:=len(buf)
  if readErr!=nil{return "",readErr}
  if n>65536||json.Unmarshal(buf[:n],&record)!=nil||record.SchemaVersion!=1{return "",&Error{Code:"MCP_DISCOVERY_INVALID",Message:"Refresh Manager discovery"}}
  path=record.MCPExecutable
 }
 name,service:="KingAIMcpServer","KingAIRuntime";if runtime.GOOS=="windows" {name+=".exe";service+=".exe"}
 if !filepath.IsAbs(path)||!strings.EqualFold(filepath.Base(path),name){return "",&Error{Code:"MCP_PATH_INVALID",Message:"Specify the absolute installed MCP path"}}
 for _,p:=range []string{path,filepath.Join(filepath.Dir(path),service)}{s,err:=os.Stat(p);if err!=nil||!s.Mode().IsRegular(){return "",&Error{Code:"MCP_NOT_INSTALLED",Message:"MCP/Runtime missing"}}}
 return filepath.EvalSymlinks(path)
}

func environment(o Options)([]string,error){
 allowed:=map[string]bool{};for _,k:=range strings.Fields("systemroot windir systemdrive comspec pathext programfiles programfiles(x86) programw6432 programdata userprofile appdata localappdata homedrive homepath username userdomain temp tmp home lang lc_all lc_ctype tmpdir display wayland_display xdg_runtime_dir"){allowed[k]=true}
 env:=[]string{};for _,entry:=range os.Environ(){key,_,_:=strings.Cut(entry,"=");if allowed[strings.ToLower(key)]{env=append(env,entry)}}
 path:="/usr/bin:/bin:/usr/sbin:/sbin";if runtime.GOOS=="windows"{root:=os.Getenv("SystemRoot");if root==""{return nil,errors.New("SystemRoot is required")};path=filepath.Join(root,"System32")+";"+root}
 env=append(env,"PATH="+path)
 if o.Language!=""{env=append(env,"KINGAI_MCP_LANGUAGE="+o.Language)}
 for key,p:=range map[string]string{"KINGAI_MCP_DOWNLOAD_DIR":o.DownloadDir,"KINGAI_MCP_ARTIFACT_DIR":o.ArtifactDir}{if p!=""{if !filepath.IsAbs(p){return nil,fmt.Errorf("%s must be absolute",key)};env=append(env,key+"="+p)}}
 if len(o.FileRoots)>128{return nil,errors.New("too many file roots")}
 for _,p:=range o.FileRoots{if !filepath.IsAbs(p)||strings.Contains(p,";"){return nil,errors.New("file roots must be absolute without semicolons")}}
 if o.FileRoots!=nil{env=append(env,"KINGAI_MCP_FILE_ROOTS="+strings.Join(o.FileRoots,";"))};return env,nil
}

type Client struct { mu sync.Mutex; session *mcp.ClientSession; timeout time.Duration; closed bool; cancel context.CancelFunc }
func Connect(ctx context.Context,o Options)(*Client,error){
 path,err:=Discover(o.MCPExecutable);if err!=nil{return nil,err}
 env,err:=environment(o);if err!=nil{return nil,err}
 timeout:=o.Timeout;if timeout==0{timeout=360*time.Second};if timeout<0{return nil,errors.New("timeout must be positive")}
 cmd:=exec.Command(path);cmd.Dir=filepath.Dir(path);cmd.Env=env;configureProcess(cmd)
 sdk:=mcp.NewClient(&mcp.Implementation{Name:"kingai-go",Version:"0.3.0"},nil)
 // The protocol connection uses a lifetime context, not a handshake context
 // cancelled immediately after Connect returns.
 life,cancel:=context.WithCancel(context.Background())
 stopCaller:=context.AfterFunc(ctx,cancel);timer:=time.AfterFunc(timeout,cancel)
 session,err:=sdk.Connect(life,&mcp.CommandTransport{Command:cmd},nil)
 stopCaller();timer.Stop()
 if err!=nil{cancel();return nil,&Error{Code:"MCP_START_FAILED",Message:err.Error()}}
 if life.Err()!=nil{_ = session.Close();cancel();return nil,&Error{Code:"MCP_START_FAILED",Message:"Initialization cancelled or timed out"}}
 return &Client{session:session,timeout:timeout,cancel:cancel},nil
}
func (c *Client) Close()error{c.mu.Lock();defer c.mu.Unlock();if c.closed{return nil};c.closed=true;defer c.cancel();return c.session.Close()}

func decode(result *mcp.CallToolResult)(any,error){
 data,err:=json.Marshal(result.StructuredContent)
 var raw Arguments
 if err==nil{_ = json.Unmarshal(data,&raw)}
 if _,ok:=raw["ok"].(bool);!ok{
  var texts []string;for _,content:=range result.Content{if t,ok:=content.(*mcp.TextContent);ok{texts=append(texts,t.Text)}}
  dec:=json.NewDecoder(strings.NewReader(strings.Join(texts,"\n")));dec.UseNumber();raw=nil
  var trailing any
  if dec.Decode(&raw)!=nil||dec.Decode(&trailing)!=io.EOF{raw=nil}
 }
 ok,present:=raw["ok"].(bool)
 if present&&!ok{code,_:=raw["code"].(string);message,_:=raw["message"].(string);if code==""{code="KINGAI_ERROR"};if message==""{message,_=raw["error"].(string)};return nil,&Error{Code:code,Message:message,Details:raw}}
 if present&&ok&&!result.IsError{return raw["result"],nil}
 if result.IsError{return nil,&Error{Code:"MCP_TOOL_ERROR",Message:"MCP reported a tool error"}}
 return nil,&Error{Code:"INVALID_TOOL_RESPONSE",Message:"No valid KingAI envelope; inspect state before repeating",OutcomeUnknown:true}
}
func (c *Client) call(ctx context.Context,name string,args Arguments)(any,error){
 if c.closed{return nil,&Error{Code:"CLIENT_CLOSED",Message:"Create a new client"}}
 if name==""{return nil,errors.New("tool name is required")};for _,ch:=range name{if !(ch>='a'&&ch<='z'||ch>='0'&&ch<='9'||ch=='_'){return nil,errors.New("invalid tool name")}}
 if err:=ctx.Err();err!=nil{return nil,err}
 // Validate/snapshot JSON before dispatch so local serialization errors are definite.
 data,err:=json.Marshal(args);if err!=nil{return nil,err};copyArgs:=Arguments{};if args!=nil{dec:=json.NewDecoder(bytes.NewReader(data));dec.UseNumber();if err=dec.Decode(&copyArgs);err!=nil{return nil,err}}
 requestCtx,cancel:=context.WithTimeout(ctx,c.timeout);defer cancel()
 result,err:=c.session.CallTool(requestCtx,&mcp.CallToolParams{Name:name,Arguments:copyArgs})
 if err!=nil{return nil,&Error{Code:"OUTCOME_UNKNOWN",Message:err.Error(),OutcomeUnknown:true}}
 return decode(result)
}
func (c *Client) Call(ctx context.Context,name string,args Arguments)(any,error){c.mu.Lock();defer c.mu.Unlock();return c.call(ctx,name,args)}
func (c *Client) Tools(ctx context.Context)([]*mcp.Tool,error){
 c.mu.Lock();defer c.mu.Unlock();if c.closed{return nil,&Error{Code:"CLIENT_CLOSED",Message:"Create a new client"}}
 ctx,cancel:=context.WithTimeout(ctx,c.timeout);defer cancel();var tools []*mcp.Tool;cursor:="";seen:=map[string]bool{}
 for{result,err:=c.session.ListTools(ctx,&mcp.ListToolsParams{Cursor:cursor});if err!=nil{return nil,err};tools=append(tools,result.Tools...);cursor=result.NextCursor;if cursor==""{return tools,nil};if seen[cursor]{return nil,errors.New("repeated tool cursor")};seen[cursor]=true}
}
func (c *Client) Info(ctx context.Context)(any,error){return c.Call(ctx,"sdk_info",nil)}
func (c *Client) Profiles(ctx context.Context)(any,error){return c.Call(ctx,"profiles_list",nil)}
func (c *Client) Profile(ctx context.Context,id string)(any,error){return c.Call(ctx,"profiles_get",Arguments{"profile_id":id})}
func (c *Client) CreateProfile(ctx context.Context,name string,options Arguments)(any,error){a:=clone(options);a["name"]=name;return c.Call(ctx,"profiles_create",a)}
func (c *Client) UpdateProfile(ctx context.Context,id string,options Arguments)(any,error){a:=clone(options);a["profile_id"]=id;return c.Call(ctx,"profiles_update",a)}
func (c *Client) DeleteProfile(ctx context.Context,id string,confirm bool)(any,error){return c.Call(ctx,"profiles_delete",Arguments{"profile_id":id,"confirm":confirm})}
func (c *Client) Sessions(ctx context.Context)(any,error){return c.Call(ctx,"browser_sessions_list",nil)}
func (c *Client) RequestStatus(ctx context.Context,id string)(any,error){return c.Call(ctx,"runtime_request_status",Arguments{"request_id":id})}
func clone(a Arguments)Arguments{b:=Arguments{};for k,v:=range a{b[k]=v};return b}
type Session struct { Client *Client; ID string; Info any }
func (c *Client) Start(ctx context.Context,options Arguments)(*Session,error){r,err:=c.Call(ctx,"browser_start",options);if err!=nil{return nil,err};m,ok:=r.(map[string]any);if !ok{return nil,&Error{Code:"INVALID_TOOL_RESPONSE",Message:"Start returned no session",OutcomeUnknown:true}};id,_:=m["sessionId"].(string);if id==""{return nil,&Error{Code:"INVALID_TOOL_RESPONSE",Message:"Start returned no sessionId",OutcomeUnknown:true}};return &Session{c,id,r},nil}
func (c *Client) Attach(ctx context.Context,id string)(*Session,error){r,err:=c.Call(ctx,"browser_attach",Arguments{"session_id":id});if err!=nil{return nil,err};return &Session{c,id,r},nil}
func (s *Session) Call(ctx context.Context,name string,args Arguments)(any,error){a:=clone(args);a["session_id"]=s.ID;return s.Client.Call(ctx,name,a)}
// Observe holds the same client lock across the operation AND all observation calls.
func (s *Session) Observe(ctx context.Context,name string,args Arguments)(any,error){
 c:=s.Client;c.mu.Lock();defer c.mu.Unlock();a:=clone(args);a["session_id"]=s.ID;r,err:=c.call(ctx,name,a);if err!=nil{return nil,err}
 out:=Arguments{"operationStatus":"returned","operationResult":r,"businessOutcome":"not_verified"};state:=Arguments{}
 for _,item:=range [][2]string{{"page","browser_read"},{"snapshot","browser_snapshot"},{"tabs","tabs_list"}}{v,e:=c.call(ctx,item[1],Arguments{"session_id":s.ID});if e!=nil{out["observationStatus"]="unavailable";out["observationError"]=e.Error();out["hint"]="Observe again; do not repeat the previous input";return out,nil};state[item[0]]=v}
 out["observationStatus"]="captured";out["observation"]=state;return out,nil
}
func (s *Session) Goto(ctx context.Context,url string)(any,error){return s.Call(ctx,"browser_navigate",Arguments{"url":url})}
func (s *Session) NewTab(ctx context.Context,url string)(any,error){a:=Arguments{};if url!=""{a["url"]=url};return s.Call(ctx,"tabs_new",a)}
func (s *Session) Click(ctx context.Context,ref string)(any,error){return s.Call(ctx,"browser_click",Arguments{"ref":ref})}
func (s *Session) Fill(ctx context.Context,ref,text string)(any,error){return s.Call(ctx,"browser_fill",Arguments{"ref":ref,"text":text})}
func (s *Session) Read(ctx context.Context)(any,error){return s.Call(ctx,"browser_read",nil)}
func (s *Session) Snapshot(ctx context.Context,args Arguments)(any,error){return s.Call(ctx,"browser_snapshot",args)}
func (s *Session) Query(ctx context.Context,args Arguments)(any,error){return s.Call(ctx,"browser_query",args)}
func (s *Session) Tabs(ctx context.Context)(any,error){return s.Call(ctx,"tabs_list",nil)}
func (s *Session) ActivateTab(ctx context.Context,id string)(any,error){return s.Call(ctx,"tabs_activate",Arguments{"target_id":id})}
func (s *Session) CloseTab(ctx context.Context,id string)(any,error){return s.Call(ctx,"tabs_close",Arguments{"target_id":id})}
func (s *Session) Evaluate(ctx context.Context,expression string)(any,error){return s.Call(ctx,"browser_evaluate",Arguments{"expression":expression})}
func (s *Session) Detach(ctx context.Context)(any,error){return s.Call(ctx,"browser_detach",nil)}
func (s *Session) Close(ctx context.Context)(any,error){return s.Call(ctx,"browser_close",nil)}
