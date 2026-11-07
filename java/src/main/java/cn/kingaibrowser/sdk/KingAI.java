package cn.kingaibrowser.sdk;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** Local MCP tools client. No HTTP, raw CDP, automatic replay or browser-tree killing. */
public final class KingAI implements AutoCloseable {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final int MAX_MESSAGE = 32 * 1024 * 1024;
    private static final boolean WINDOWS = System.getProperty("os.name").toLowerCase(Locale.ROOT).contains("win");
    private static final Set<String> VERSIONS = Set.of("2024-11-05","2025-03-26","2025-06-18","2025-11-25");

    public static final class KingAIException extends RuntimeException {
        public final String code; public final JsonNode details; public final boolean outcomeUnknown;
        KingAIException(String code,String message,JsonNode details,boolean unknown) {
            super(message); this.code=code; this.details=details; this.outcomeUnknown=unknown;
        }
    }
    public static final class Options {
        public Path mcpExecutable; public Duration timeout=Duration.ofSeconds(360);
        public String language; public List<Path> fileRoots=List.of(); public Path downloadDir,artifactDir;
    }
    private final Process process;
    private final Duration timeout;
    private final ConcurrentMap<Long,CompletableFuture<JsonNode>> pending=new ConcurrentHashMap<>();
    private final AtomicLong ids=new AtomicLong();
    private final ExecutorService writer;
    private volatile boolean closed=false;
    private volatile Throwable disconnected;
    public final JsonNode serverInfo;

    public static Path discover(Path explicit) throws IOException {
        Path path=explicit;
        if(path==null) {
            String value=System.getenv("KINGAI_MCP_EXECUTABLE");
            if(value!=null&&!value.isBlank())path=Path.of(value);
        }
        if(path==null) {
            Path home=Path.of(System.getProperty("user.home"));
            Path root=home.resolve(".config/KingAIBrowser");
            if(WINDOWS) {
                String local=System.getenv("LOCALAPPDATA");
                if(local==null)throw failure("MCP_NOT_FOUND","LOCALAPPDATA missing; specify the installed MCP",false);
                root=Path.of(local).resolve("KingAIBrowser");
            } else if(System.getProperty("os.name").toLowerCase(Locale.ROOT).contains("mac"))root=home.resolve("Library/Application Support/KingAIBrowser");
            Path file=root.resolve("sdk-installation.json");
            if(!Files.isRegularFile(file))throw failure("MCP_NOT_FOUND","Open Manager once or specify the MCP executable",false);
            try(InputStream input=Files.newInputStream(file)) {
                byte[] bytes=input.readNBytes(65537);
                if(bytes.length>65536)throw failure("MCP_DISCOVERY_INVALID","Discovery file too large",false);
                JsonNode record=JSON.readTree(bytes);
                if(record==null||record.path("schemaVersion").asInt()!=1||!record.path("mcpExecutable").isTextual())throw failure("MCP_DISCOVERY_INVALID","Refresh Manager discovery",false);
                path=Path.of(record.get("mcpExecutable").asText());
            }
        }
        String expected=WINDOWS?"KingAIMcpServer.exe":"KingAIMcpServer";
        if(!path.isAbsolute()||!path.getFileName().toString().equalsIgnoreCase(expected))throw failure("MCP_PATH_INVALID","Specify an absolute installed MCP executable",false);
        if(!Files.isRegularFile(path)||!Files.isRegularFile(path.resolveSibling(WINDOWS?"KingAIRuntime.exe":"KingAIRuntime")))throw failure("MCP_NOT_INSTALLED","MCP/Runtime missing",false);
        return path.toRealPath();
    }
    private static KingAIException failure(String code,String message,boolean unknown) {return new KingAIException(code,message,null,unknown);}
    private static void configureEnvironment(Map<String,String> env,Options o) {
        Set<String> allowed=new HashSet<>(Arrays.asList(("systemroot windir systemdrive comspec pathext programfiles programfiles(x86) programw6432 programdata userprofile appdata localappdata homedrive homepath username userdomain temp tmp home lang lc_all lc_ctype tmpdir display wayland_display xdg_runtime_dir").split(" ")));
        env.entrySet().removeIf(e->!allowed.contains(e.getKey().toLowerCase(Locale.ROOT)));
        if(WINDOWS) {
            String root=System.getenv("SystemRoot");if(root==null)throw new IllegalArgumentException("SystemRoot missing");
            env.put("PATH",Path.of(root,"System32")+";"+root);
        } else env.put("PATH","/usr/bin:/bin:/usr/sbin:/sbin");
        if(o.language!=null)env.put("KINGAI_MCP_LANGUAGE",o.language);
        for(var entry:Map.of("KINGAI_MCP_DOWNLOAD_DIR",Optional.ofNullable(o.downloadDir),"KINGAI_MCP_ARTIFACT_DIR",Optional.ofNullable(o.artifactDir)).entrySet()) {
            entry.getValue().ifPresent(path->{if(!path.isAbsolute())throw new IllegalArgumentException("Artifact/download path must be absolute");env.put(entry.getKey(),path.toString());});
        }
        if(o.fileRoots.size()>128)throw new IllegalArgumentException("Too many file roots");
        List<String> roots=new ArrayList<>();
        for(Path root:o.fileRoots){if(!root.isAbsolute()||root.toString().contains(";"))throw new IllegalArgumentException("Invalid file root");roots.add(root.toString());}
        env.put("KINGAI_MCP_FILE_ROOTS",String.join(";",roots));
    }
    public KingAI() throws IOException {this(new Options());}
    public KingAI(Options options) throws IOException {
        if(options.timeout==null||options.timeout.isNegative()||options.timeout.isZero())throw new IllegalArgumentException("timeout must be positive");
        timeout=options.timeout;Path path=discover(options.mcpExecutable);
        ProcessBuilder builder=new ProcessBuilder(path.toString()).directory(path.getParent().toFile()).redirectError(ProcessBuilder.Redirect.INHERIT);
        configureEnvironment(builder.environment(),options);process=builder.start();
        ThreadFactory threads=r->{Thread t=new Thread(r,"kingai-mcp-writer");t.setDaemon(true);return t;};
        writer=new ThreadPoolExecutor(1,1,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(64),threads,new ThreadPoolExecutor.AbortPolicy());
        Thread reader=new Thread(this::readLoop,"kingai-mcp-reader");reader.setDaemon(true);reader.start();
        JsonNode initialized;
        try {
            initialized=request("initialize",Map.of("protocolVersion","2025-11-25","capabilities",Map.of(),"clientInfo",Map.of("name","kingai-java","version","0.3.0")),false);
            if(!VERSIONS.contains(initialized.path("protocolVersion").asText()))throw failure("MCP_VERSION_MISMATCH","Unsupported negotiated version",false);
            if(!initialized.path("capabilities").has("tools"))throw failure("MCP_TOOLS_UNAVAILABLE","Server does not advertise tools",false);
            send(JSON.createObjectNode().put("jsonrpc","2.0").put("method","notifications/initialized"));
        } catch(RuntimeException error){close();throw error;}
        serverInfo=initialized;
    }
    private void failPending(Throwable error) {
        disconnected=error;pending.forEach((id,future)->future.completeExceptionally(error));pending.clear();
    }
    private void send(JsonNode message) {
        final byte[] bytes;
        try {bytes=(JSON.writeValueAsString(message)+"\n").getBytes(StandardCharsets.UTF_8);}catch(IOException error){throw new IllegalArgumentException("Invalid JSON",error);}
        if(bytes.length>MAX_MESSAGE)throw new IllegalArgumentException("Message exceeds 32 MiB");
        if(closed||disconnected!=null)throw failure("MCP_DISCONNECTED","The connection is closed",false);
        try {writer.execute(()->{try{process.getOutputStream().write(bytes);process.getOutputStream().flush();}catch(IOException error){failPending(error);}});}
        catch(RejectedExecutionException error){throw failure("MCP_QUEUE_FULL","The message was not queued",false);}
    }
    private void readLoop() {
        try(InputStream input=new BufferedInputStream(process.getInputStream())) {
            while(true) {
                ByteArrayOutputStream line=new ByteArrayOutputStream();int b;
                while((b=input.read())!=-1&&b!='\n'){if(line.size()>=MAX_MESSAGE)throw new IOException("Oversized MCP message");line.write(b);}
                if(b==-1)throw new EOFException("MCP stdout closed");
                JsonNode message=JSON.readTree(line.toByteArray());
                if(message==null||!message.isObject()||!message.path("jsonrpc").asText().equals("2.0"))throw new IOException("Invalid JSON-RPC message");
                if(message.has("method")) {
                    if(message.has("id")) {
                        ObjectNode reply=JSON.createObjectNode().put("jsonrpc","2.0");reply.set("id",message.get("id"));
                        if(message.path("method").asText().equals("ping"))reply.set("result",JSON.createObjectNode());
                        else reply.set("error",JSON.createObjectNode().put("code",-32601).put("message","Client method not supported"));
                        send(reply);
                    }
                    continue;
                }
                if(!message.path("id").isIntegralNumber()||message.has("result")==message.has("error"))throw new IOException("Invalid MCP response");
                CompletableFuture<JsonNode> target=pending.remove(message.get("id").asLong());if(target!=null)target.complete(message);
            }
        } catch(Exception error){failPending(error);}
    }
    private synchronized JsonNode request(String method,Object args,boolean tool) {
        if(closed||disconnected!=null)throw failure("MCP_DISCONNECTED","Create a new client; no automatic reconnect",false);
        long id=ids.incrementAndGet();CompletableFuture<JsonNode> target=new CompletableFuture<>();pending.put(id,target);
        try {
            ObjectNode request=JSON.createObjectNode().put("jsonrpc","2.0").put("id",id).put("method",method);request.set("params",JSON.valueToTree(args));send(request);
            JsonNode response=target.get(timeout.toMillis(),TimeUnit.MILLISECONDS);
            if(response.has("error"))throw new KingAIException("MCP_RPC_ERROR","MCP returned a JSON-RPC error",response.get("error"),tool);
            return response.get("result");
        } catch(TimeoutException|ExecutionException error){throw failure(tool?"OUTCOME_UNKNOWN":"MCP_TIMEOUT","No usable response; inspect session state before repeating an action",tool);}
        catch(InterruptedException error){Thread.currentThread().interrupt();throw failure(tool?"OUTCOME_UNKNOWN":"MCP_INTERRUPTED","Request interrupted; do not replay side effects",tool);}
        finally{pending.remove(id);}
    }
    public synchronized JsonNode call(String name,Map<String,?> args) {
        if(name==null||!name.matches("[a-z][a-z0-9_]*"))throw new IllegalArgumentException("Invalid tool name");
        JsonNode response=request("tools/call",Map.of("name",name,"arguments",args==null?Map.of():args),true);
        JsonNode envelope=response.get("structuredContent");
        if(envelope==null||!envelope.path("ok").isBoolean()) {
            StringJoiner text=new StringJoiner("\n");for(JsonNode part:response.path("content"))if(part.path("type").asText().equals("text"))text.add(part.path("text").asText());
            try{envelope=JSON.readTree(text.toString());}catch(IOException error){envelope=null;}
        }
        if(envelope!=null&&envelope.path("ok").isBoolean()) {
            if(!envelope.get("ok").asBoolean())throw new KingAIException(envelope.path("code").asText("KINGAI_ERROR"),envelope.path("message").asText(envelope.path("error").asText()),envelope,false);
            if(!response.path("isError").asBoolean())return envelope.path("result");
        }
        if(response.path("isError").asBoolean())throw new KingAIException("MCP_TOOL_ERROR","MCP reported a tool error",response,false);
        throw new KingAIException("INVALID_TOOL_RESPONSE","Inspect state before repeating an operation",response,true);
    }
    public synchronized List<JsonNode> tools() {
        List<JsonNode> tools=new ArrayList<>();Set<String> seen=new HashSet<>();String cursor=null;
        do {JsonNode result=request("tools/list",cursor==null?Map.of():Map.of("cursor",cursor),false);
            if(!result.path("tools").isArray())throw failure("INVALID_TOOL_RESPONSE","Invalid tools/list",false);
            result.get("tools").forEach(tools::add);cursor=result.hasNonNull("nextCursor")?result.get("nextCursor").asText():null;
            if(cursor!=null&&!seen.add(cursor))throw failure("INVALID_TOOL_RESPONSE","Repeated tool cursor",false);
        }while(cursor!=null);return tools;
    }
    public JsonNode info(){return call("sdk_info",Map.of());}
    public JsonNode profiles(){return call("profiles_list",Map.of());}
    public JsonNode profile(String id){return call("profiles_get",Map.of("profile_id",id));}
    public JsonNode createProfile(String name){return createProfile(name,Map.of());}
    public JsonNode createProfile(String name,Map<String,?> options){Map<String,Object> a=copy(options);a.put("name",name);return call("profiles_create",a);}
    public JsonNode updateProfile(String id,Map<String,?> options){Map<String,Object>a=copy(options);a.put("profile_id",id);return call("profiles_update",a);}
    public JsonNode deleteProfile(String id,boolean confirm){return call("profiles_delete",Map.of("profile_id",id,"confirm",confirm));}
    public JsonNode sessions(){return call("browser_sessions_list",Map.of());}
    public JsonNode skills(){return call("skills_list",Map.of());}
    public JsonNode runSkill(String profileId,String skillId,Map<String,?> options){Map<String,Object>a=copy(options);a.put("profile_id",profileId);a.put("skill_id",skillId);return call("skill_run",a);}
    public JsonNode skillStatus(String id){return call("skill_status",Map.of("run_id",id));}
    public JsonNode cancelSkill(String id){return call("skill_cancel",Map.of("run_id",id));}
    public JsonNode requestStatus(String id){return call("runtime_request_status",Map.of("request_id",id));}
    public Session start(){return start(Map.of());}
    public Session start(Map<String,?> options){JsonNode info=call("browser_start",options);String id=info.path("sessionId").asText();if(id.isBlank())throw failure("INVALID_TOOL_RESPONSE","No sessionId; inspect sessions before restarting",true);return new Session(this,id,info);}
    public Session attach(String id){return new Session(this,id,call("browser_attach",Map.of("session_id",id)));}
    private static Map<String,Object> copy(Map<String,?> source){Map<String,Object>a=new LinkedHashMap<>();if(source!=null)a.putAll(source);return a;}

    public static BrowserInstaller.Result install(Path downloadDir, boolean downloadOnly, String expectedSha256) throws IOException, InterruptedException {
        BrowserInstaller.Result downloaded = BrowserInstaller.download(downloadDir, expectedSha256);
        return downloadOnly ? downloaded : BrowserInstaller.openInstaller(downloaded);
    }
    public static Session launch() throws IOException { return launch(new Options(), null); }
    public static Session launch(Options options, String profileId) throws IOException {
        KingAI api = new KingAI(options);
        try {
            Session browser = api.start(profileId == null ? Map.of() : Map.of("profile_id", profileId));
            browser.ownsClient = true;
            return browser;
        } catch (RuntimeException error) { api.close(); throw error; }
    }

    public static final class Session implements AutoCloseable {
        private boolean ownsClient;
        public final KingAI client; public final String sessionId; public final JsonNode info;
        private Session(KingAI client,String id,JsonNode info){this.client=client;this.sessionId=id;this.info=info;}
        public JsonNode call(String name,Map<String,?> options){Map<String,Object>a=copy(options);a.put("session_id",sessionId);return client.call(name,a);}
        public JsonNode observe(String name,Map<String,?> options) {
            synchronized(client) {
                JsonNode result=call(name,options);ObjectNode out=JSON.createObjectNode().put("operationStatus","returned").put("businessOutcome","not_verified");out.set("operationResult",result);
                try {ObjectNode state=JSON.createObjectNode();state.set("page",read());state.set("snapshot",snapshot(Map.of()));state.set("tabs",tabs());out.set("observation",state);out.put("observationStatus","captured");}
                catch(RuntimeException error){out.put("observationStatus","unavailable").put("observationError",error.getMessage()).put("hint","Observe again; do not repeat the input");}
                return out;
            }
        }
        public JsonNode gotoUrl(String url){return call("browser_navigate",Map.of("url",url));}
        public JsonNode newTab(String url){return call("tabs_new",url==null?Map.of():Map.of("url",url));}
        public JsonNode tabs(){return call("tabs_list",Map.of());}
        public JsonNode activateTab(String id){return call("tabs_activate",Map.of("target_id",id));}
        public JsonNode closeTab(String id){return call("tabs_close",Map.of("target_id",id));}
        public JsonNode click(String ref){return call("browser_click",Map.of("ref",ref));}
        public JsonNode click(String ref,Map<String,?> options){Map<String,Object>a=copy(options);a.put("ref",ref);return call("browser_click",a);}
        public JsonNode fill(String ref,String text){return call("browser_fill",Map.of("ref",ref,"text",text));}
        public JsonNode fill(String ref,String text,Map<String,?> options){Map<String,Object>a=copy(options);a.put("ref",ref);a.put("text",text);return call("browser_fill",a);}
        public JsonNode type(String ref,String text,Map<String,?> options){Map<String,Object>a=copy(options);a.put("ref",ref);a.put("text",text);return call("browser_type",a);}
        public JsonNode type(String ref,String text){return type(ref,text,Map.of());}
        public JsonNode hover(String ref,Map<String,?> options){Map<String,Object>a=copy(options);a.put("ref",ref);return call("browser_hover",a);}
        public JsonNode hover(String ref){return hover(ref,Map.of());}
        public JsonNode waitFor(Map<String,?> options){return call("browser_wait",options);}
        public JsonNode read(){return call("browser_read",Map.of());}
        public JsonNode snapshot(Map<String,?> args){return call("browser_snapshot",args);}
        public JsonNode query(Map<String,?> args){return call("browser_query",args);}
        public JsonNode evaluate(String expression){return call("browser_evaluate",Map.of("expression",expression));}
        public JsonNode evaluatePreview(String expression){
            if(expression==null||expression.isBlank())throw new IllegalArgumentException("expression must not be empty");
            try(InputStream body=KingAI.class.getResourceAsStream("preview-body.js")) {
                if(body==null)throw new IllegalStateException("Missing preview resource; use the complete JAR");
                String wrapped="(async () => { const source = await (\n"+expression+"\n);"+new String(body.readAllBytes(),StandardCharsets.UTF_8);
                return evaluate(wrapped);
            } catch(IOException error){throw new UncheckedIOException(error);}
        }
        public JsonNode scroll(double deltaY){return call("browser_scroll",Map.of("delta_y",deltaY));}
        public JsonNode key(String key,List<String> modifiers){return call("browser_key",Map.of("key",key,"modifiers",modifiers));}
        public JsonNode screenshot(Map<String,?> options){return call("browser_screenshot",options);}
        public JsonNode pdf(Map<String,?> options){return call("browser_pdf",options);}
        public JsonNode cookies(){return call("cookies_list",Map.of());}
        public JsonNode storage(Map<String,?> options){return call("storage_get",options);}
        public JsonNode upload(String ref,List<String> paths){return call("browser_upload",Map.of("ref",ref,"paths",paths));}
        public JsonNode download(String ref){return call("browser_download",Map.of("ref",ref));}
        public JsonNode detach(){try{return call("browser_detach",Map.of());}finally{if(ownsClient)client.close();}}
        public void disconnect(){if(!ownsClient)throw new IllegalStateException("Session does not own its client");client.close();}
        /** Automatic resource cleanup preserves the browser and only owns launch clients. */
        @Override public void close(){if(ownsClient&&!client.closed)detach();}
        /** Explicitly closes this browser, unlike client.close(). */
        public JsonNode closeBrowser(){if(client.closed)throw failure("SESSION_DISCONNECTED","This session is disconnected; use Manager or explicitly attach a new authorized client to the active session",false);try{return call("browser_close",Map.of());}finally{if(ownsClient)client.close();}}
    }
    @Override public synchronized void close() {
        if(closed)return;closed=true;writer.shutdownNow();failPending(new IOException("Client closed"));
        Thread closer=new Thread(()->{try{process.getOutputStream().close();}catch(IOException ignored){}},"kingai-mcp-close");closer.setDaemon(true);closer.start();
        try{if(!process.waitFor(3,TimeUnit.SECONDS)){process.destroy();if(!process.waitFor(3,TimeUnit.SECONDS)){process.destroyForcibly();if(!process.waitFor(3,TimeUnit.SECONDS))throw failure("MCP_SHUTDOWN_FAILED","Owned MCP process did not exit",false);}}}
        catch(InterruptedException error){Thread.currentThread().interrupt();process.destroy();}
    }
}
