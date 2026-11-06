package kingai

import (
 "context"
 _ "embed"
 "errors"
 "strings"
)

//go:embed preview-body.js
var previewBody string

// EvaluatePreview runs the expression once and returns a bounded result preview.
// Evaluate keeps raw MCP semantics. No automatic replay happens after any error.
func (s *Session) EvaluatePreview(ctx context.Context,expression string)(any,error){
 if strings.TrimSpace(expression)==""{return nil,errors.New("expression must not be empty")}
 wrapped:="(async () => { const source = await (\n"+expression+"\n);"+previewBody
 return s.Call(ctx,"browser_evaluate",Arguments{"expression":wrapped})
}
func (s *Session) Scroll(ctx context.Context,dy float64)(any,error){return s.Call(ctx,"browser_scroll",Arguments{"delta_y":dy})}
func (s *Session) Key(ctx context.Context,key string,modifiers []string)(any,error){return s.Call(ctx,"browser_key",Arguments{"key":key,"modifiers":modifiers})}
func (s *Session) Screenshot(ctx context.Context,args Arguments)(any,error){return s.Call(ctx,"browser_screenshot",args)}
func (s *Session) PDF(ctx context.Context,args Arguments)(any,error){return s.Call(ctx,"browser_pdf",args)}
func (s *Session) Cookies(ctx context.Context)(any,error){return s.Call(ctx,"cookies_list",nil)}
func (s *Session) Storage(ctx context.Context,args Arguments)(any,error){return s.Call(ctx,"storage_get",args)}
func (s *Session) Upload(ctx context.Context,ref string,paths []string)(any,error){return s.Call(ctx,"browser_upload",Arguments{"ref":ref,"paths":paths})}
func (s *Session) Download(ctx context.Context,ref string)(any,error){return s.Call(ctx,"browser_download",Arguments{"ref":ref})}
func (c *Client) Skills(ctx context.Context)(any,error){return c.Call(ctx,"skills_list",nil)}
func (c *Client) RunSkill(ctx context.Context,profileID,skillID string,options Arguments)(any,error){a:=clone(options);a["profile_id"]=profileID;a["skill_id"]=skillID;return c.Call(ctx,"skill_run",a)}
func (c *Client) SkillStatus(ctx context.Context,id string)(any,error){return c.Call(ctx,"skill_status",Arguments{"run_id":id})}
func (c *Client) CancelSkill(ctx context.Context,id string)(any,error){return c.Call(ctx,"skill_cancel",Arguments{"run_id":id})}
