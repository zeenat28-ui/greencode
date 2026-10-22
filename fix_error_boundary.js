const fs = require("fs");
let src = fs.readFileSync("frontend/src/App.tsx", "utf8");

// Replace entire render() method content in ErrorBoundary
src = src.replace(
  /render\(\) \{[\s\S]*?return this\.props\.children;\s*\}\s*\}/,
  `render() {
    if (this.state.hasError) {
      const msg = this.state.error ? this.state.error.message : "Unknown error";
      const stack = this.state.error ? (this.state.error.stack || "") : "";
      return (
        <div style={{padding:24,background:"#0a0a0a",color:"#f87171",minHeight:"100vh",fontFamily:"monospace"}}>
          <h2 style={{color:"#f87171",marginBottom:12}}>GreenCode Dashboard Error:</h2>
          <pre style={{whiteSpace:"pre-wrap",fontSize:12,color:"#fca5a5",background:"#111",padding:16,borderRadius:8,overflow:"auto"}}>
            {msg + "\\n\\n" + stack}
          </pre>
          <button onClick={() => window.location.reload()}
            style={{marginTop:16,padding:"8px 20px",background:"#10b981",color:"white",border:"none",borderRadius:6,cursor:"pointer"}}>
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}`
);

fs.writeFileSync("frontend/src/App.tsx", src, {encoding:"utf8"});
console.log("Done. Size:", src.length);
