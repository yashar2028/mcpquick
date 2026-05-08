export default function FaqPage() {
  return (
    <section className="stack">
      <article className="panel faq-hero">
        <h2>FAQ</h2>
        <p className="muted">
          Answers to common MCP Quick workflow questions.
        </p>
      </article>
      <div className="faq-grid">
        <div className="faq-item">
          <h3>Which providers are supported?</h3>
          <p>
            Anthropic, OpenAI, and Gemini are available today. Provider options
            can be selected when you create a new run.
          </p>
        </div>
        <div className="faq-item">
          <h3>How are MCP servers configured?</h3>
          <p>
            Add an MCP repo URL and server.json path in the run form. MCP support
            for tool calling currently targets Anthropic models in v1.
          </p>
        </div>
        <div className="faq-item">
          <h3>Where do API keys live?</h3>
          <p>
            API keys are stored in memory for the run session only and are not
            persisted in the backend.
          </p>
        </div>
        <div className="faq-item">
          <h3>What should I do when a run fails?</h3>
          <p>
            Open the run details page to review sandbox logs, then retry with a
            new key or updated MCP configuration.
          </p>
        </div>
      </div>
    </section>
  );
}
