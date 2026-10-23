import { ArrowLeft, ExternalLink, Leaf, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import AlexaVoiceCockpit from "../components/common/AlexaVoiceCockpit";

export default function AlexaDemo() {
  return (
    <main className="min-h-screen bg-[#f5f7f6] px-4 py-8 text-zinc-900 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-medium text-zinc-600 transition hover:text-zinc-950"
          >
            <ArrowLeft size={16} />
            GreenCode
          </Link>
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800">
            <ShieldCheck size={14} />
            Local MCP demo
          </span>
        </header>

        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm sm:p-10">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800">
              <Leaf size={24} />
            </div>
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-800">
                Alexa+ style web simulator
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                Ask GreenCode about software energy
              </h1>
              <p className="mt-3 text-sm leading-6 text-zinc-600 sm:text-base">
                Try a region comparison, code audit, or refactor proposal. Each
                preset initializes a real MCP session, lists the server tools,
                and calls GreenCode&apos;s local MCP server. Results are returned
                by the tool; this page does not use scripted answer text.
              </p>
            </div>
          </div>
        </section>

        <AlexaVoiceCockpit />

        <aside className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <strong>Demo scope:</strong> This is a browser-based simulator for the
          hackathon demo. It is not an Amazon-hosted Alexa+ session, Developer
          Console test, or Echo interaction. Those require a public HTTPS
          deployment and separate Amazon-side setup. No repository access or
          cloud deployment is needed for this local demonstration.
        </aside>

        <footer className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-zinc-200 pt-4 text-sm text-zinc-600">
          <a
            href="https://github.com/zeenat28-ui/greencode"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 hover:text-zinc-950"
          >
            Source on GitHub <ExternalLink size={13} />
          </a>
          <a
            href="https://github.com/zeenat28-ui/greencode/blob/main/alexa/README.md"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 hover:text-zinc-950"
          >
            Integration notes <ExternalLink size={13} />
          </a>
        </footer>
      </div>
    </main>
  );
}
