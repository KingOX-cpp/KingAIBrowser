package cn.kingaibrowser.sdk;

import cn.kingaibrowser.sdk.samples.Sample;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class SampleTest {
    private KingAI connect() throws Exception {
        String path=System.getenv("KINGAI_TEST_MCP");assumeTrue(path!=null,"Test-only fixture executable required");
        KingAI.Options o=new KingAI.Options();o.mcpExecutable=Path.of(path);o.timeout=Duration.ofSeconds(3);return new KingAI(o);
    }
    @Test void sampleUsesRealSDKOverStdio() throws Exception {
        try(KingAI api=connect()) {
            var result=Sample.runSample(api,"sample");
            assertEquals("https://example.com",result.page().path("url").asText());
            assertEquals("Example Domain",result.page().path("title").asText());
            assertFalse(result.preview().path("truncated").asBoolean());
            String trace=api.call("fixture_trace",Map.of()).toString();
            assertTrue(trace.contains("browser_detach"));assertFalse(trace.contains("browser_close"));
        }
    }
    @Test void crudAndObservationGuards() throws Exception {
        try(KingAI api=connect()) {
            String id=api.createProfile("crud").path("profileId").asText();
            api.updateProfile(id,Map.of("name","renamed"));assertEquals("renamed",api.profile(id).path("name").asText());
            var error=assertThrows(KingAI.KingAIException.class,()->api.deleteProfile(id,false));assertEquals("CONFIRMATION_REQUIRED",error.code);
            var browser=api.start(Map.of("profile_id",id));
            error=assertThrows(KingAI.KingAIException.class,()->api.updateProfile(id,Map.of("name","busy")));assertEquals("SESSION_BUSY",error.code);
            assertEquals("captured",browser.observe("browser_click",Map.of("ref","e1")).path("observationStatus").asText());
            browser.closeBrowser();assertTrue(api.deleteProfile(id,true).path("deleted").asBoolean());
        }
    }
    @Test void decodeAndOversizeAreNotRetried() throws Exception {
        try(KingAI api=connect()) {
            var error=assertThrows(KingAI.KingAIException.class,()->api.call("fixture_bad_response",Map.of()));assertEquals("INVALID_TOOL_RESPONSE",error.code);
            var browser=api.start();api.call("fixture_fail_next",Map.of("code","RESULT_TOO_LARGE"));
            error=assertThrows(KingAI.KingAIException.class,()->browser.evaluate("document.title"));assertEquals("RESULT_TOO_LARGE",error.code);
            int count=0;for(var value:api.call("fixture_trace",Map.of()))if(value.asText().equals("browser_evaluate"))count++;
            assertEquals(1,count);
        }
    }
}
