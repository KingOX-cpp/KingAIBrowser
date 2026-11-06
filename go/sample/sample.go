// Package sample exposes the same runnable workflow used by the CLI and tests.
package sample

import("context";"errors";kingai "github.com/KingOX-cpp/KingAIBrowser/go")

type Result struct{ Info any; Profiles any; ProfileID string; Page any; Preview any }
func RunSample(ctx context.Context,api *kingai.Client,name string)(*Result,error){
 info,err:=api.Info(ctx);if err!=nil{return nil,err}
 profiles,err:=api.Profiles(ctx);if err!=nil{return nil,err}
 created,err:=api.CreateProfile(ctx,name,nil);if err!=nil{return nil,err}
 m,ok:=created.(map[string]any);if !ok{return nil,errors.New("profile creation returned no object")};id,ok:=m["profileId"].(string);if !ok||id==""{return nil,errors.New("profile creation returned no ID")}
 browser,err:=api.Start(ctx,kingai.Arguments{"profile_id":id});if err!=nil{return nil,err}
 if _,err=browser.NewTab(ctx,"https://example.com");err!=nil{return nil,err}
 page,err:=browser.Read(ctx);if err!=nil{return nil,err}
 preview,err:=browser.EvaluatePreview(ctx,"({title:document.title,text:document.body.innerText})");if err!=nil{return nil,err}
 if _,err=browser.Detach(ctx);err!=nil{return nil,err}
 return &Result{info,profiles,id,page,preview},nil
}
