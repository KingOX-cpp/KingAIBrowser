package cn.kingaibrowser.sdk.samples;

import cn.kingaibrowser.sdk.KingAI;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** The SAME method is called by the real sample CLI and the fixture-backed tests. */
public final class Sample {
    private Sample() {}
    public record Result(JsonNode info,JsonNode profiles,String profileId,JsonNode page,JsonNode preview) {}
    public static Result runSample(KingAI api,String name) {
        JsonNode info=api.info(),profiles=api.profiles();
        String id=api.createProfile(name).path("profileId").asText();
        KingAI.Session browser=api.start(Map.of("profile_id",id));
        browser.newTab("https://example.com");
        JsonNode page=browser.read();
        JsonNode preview=browser.evaluatePreview("({title:document.title,text:document.body.innerText})");
        browser.detach();
        return new Result(info,profiles,id,page,preview);
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=1||!args[0].equals("--live"))throw new IllegalArgumentException("Pass --live to create an environment in your real KingAI installation");
        try(KingAI api=new KingAI()){System.out.println(runSample(api,"Java SDK 演示"));}
    }
}
