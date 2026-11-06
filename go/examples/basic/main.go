package main

import (
 "context"
 "fmt"
 "flag"
 "log"
 kingai "github.com/KingOX-cpp/KingAIBrowser/go"
 "github.com/KingOX-cpp/KingAIBrowser/go/sample"
)

func main(){
 live:=flag.Bool("live",false,"Explicitly create a real saved environment");flag.Parse();if !*live{log.Print("Pass --live to operate your real installation");return}
 ctx:=context.Background()
 api,err:=kingai.Connect(ctx,kingai.Options{});if err!=nil{log.Fatal(err)}
 defer api.Close()
 if err=run(ctx,api);err!=nil{log.Print(err)}
}
func run(ctx context.Context,api *kingai.Client)error{
 result,err:=sample.RunSample(ctx,api,"Go SDK 演示");if err!=nil{return err};fmt.Println(result);return nil
}
