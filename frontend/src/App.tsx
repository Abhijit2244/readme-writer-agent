import React, { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import mermaid from 'mermaid';
import {
  ShieldCheck,
  Zap,
  Sparkles,
  FolderArchive,
  HardDrive,
  Copy,
  Download,
  Eye,
  Code2,
  FileText,
  AlertTriangle,
  XCircle,
  X,
  ExternalLink,
} from 'lucide-react';

const GithubIcon = ({ size = 15, style = {} }: { size?: number; style?: React.CSSProperties }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="currentColor"
    style={{ display: 'inline-block', ...style }}
  >
    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
  </svg>
);

interface TelemetryLog {
  type: string;
  data: any;
}

interface GenerationResult {
  session_id: string;
  engine_mode: string;
  output_filename: string;
  output_path: string;
  was_overwritten: boolean;
  saved_as_alternate: boolean;
  entities_documented_count: number;
  sections_included: string[];
  markdown_content: string;
  telemetry_logs: TelemetryLog[];
}

export default function App() {
  // Navigation & Engine States
  const [engine, setEngine] = useState<'local' | 'gemini'>('local');
  const [mode, setMode] = useState<'github' | 'zip' | 'local'>('github');

  // Input States
  const [githubUrl, setGithubUrl] = useState<string>('https://github.com/Abhijit2244/readme-writer-agent');
  const [repoPath, setRepoPath] = useState<string>('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [forceOverwrite, setForceOverwrite] = useState<boolean>(false);

  // Status & Telemetry States
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [telemetryLogs, setTelemetryLogs] = useState<TelemetryLog[]>([]);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [activeTab, setActiveTab] = useState<'preview' | 'raw'>('preview');

  // Notification Banner
  const [alert, setAlert] = useState<{ message: string; type: 'warn' | 'success' | 'error' } | null>(null);

  const telemetryEndRef = useRef<HTMLDivElement | null>(null);
  const previewCardRef = useRef<HTMLDivElement | null>(null);

  // Initialize Mermaid
  useEffect(() => {
    try {
      mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
    } catch (e) {
      console.warn('Mermaid initialization warning:', e);
    }
  }, []);

  // Re-render Mermaid diagrams when new markdown content arrives
  useEffect(() => {
    if (result && activeTab === 'preview') {
      setTimeout(() => {
        try {
          const container = document.getElementById('markdownRenderedContainer');
          if (container) {
            const preBlocks = container.querySelectorAll('pre code.language-mermaid');
            preBlocks.forEach((codeBlock, idx) => {
              const pre = codeBlock.parentElement;
              if (pre) {
                const graphDef = codeBlock.textContent || '';
                const div = document.createElement('div');
                div.className = 'mermaid';
                div.id = `mermaid-${Date.now()}-${idx}`;
                div.textContent = graphDef;
                pre.parentNode?.replaceChild(div, pre);
              }
            });
            mermaid.run();
          }
        } catch (e) {
          console.warn('Mermaid rendering notice:', e);
        }
      }, 50);
    }
  }, [result, activeTab]);

  // Handle generation action
  const handleGenerate = async () => {
    setAlert(null);

    // Immediately clear previous result so stale content is never visible
    setResult(null);
    setTelemetryLogs([]);

    const isGemini = engine === 'gemini';

    setIsGenerating(true);

    try {
      let endpoint = '/api/generate';
      let body: any = null;
      let headers: Record<string, string> = {};

      if (mode === 'github') {
        const url = githubUrl.trim();
        if (!url) {
          setAlert({ message: 'Please provide a valid public GitHub repository URL.', type: 'error' });
          setIsGenerating(false);
          return;
        }
        endpoint = '/api/generate-github';
        headers = { 'Content-Type': 'application/json' };
        body = JSON.stringify({
          github_url: url,
          force: forceOverwrite,
          use_gemini: isGemini,
        });
        setTelemetryLogs([{ type: 'START', data: `Fetching GitHub archive for: ${url}` }]);
      } else if (mode === 'zip') {
        if (!zipFile) {
          setAlert({ message: 'Please select a .zip project file to upload.', type: 'error' });
          setIsGenerating(false);
          return;
        }
        endpoint = '/api/upload-zip';
        const formData = new FormData();
        formData.append('file', zipFile);
        formData.append('force', String(forceOverwrite));
        formData.append('use_gemini', String(isGemini));
        body = formData;
        setTelemetryLogs([{ type: 'START', data: `Uploading and extracting project archive safely...` }]);
      } else {
        const path = repoPath.trim();
        if (!path) {
          setAlert({ message: 'Please provide a local repository filesystem path.', type: 'error' });
          setIsGenerating(false);
          return;
        }
        endpoint = '/api/generate';
        headers = { 'Content-Type': 'application/json' };
        body = JSON.stringify({
          repo_path: path,
          force: forceOverwrite,
          use_gemini: isGemini,
        });
        setTelemetryLogs([{ type: 'START', data: `Initiating inspection for local path: ${path}` }]);
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: body,
      });

      const data = await res.json();
      if (!res.ok) {
        setAlert({
          message: data.detail || 'Generation request was blocked or encountered an error.',
          type: 'error',
        });
        setTelemetryLogs((prev) => [...prev, { type: 'ERROR', data: data.detail || 'Server error' }]);
        setIsGenerating(false);
        return;
      }

      setResult(data);
      if (data.telemetry_logs && data.telemetry_logs.length) {
        setTelemetryLogs(data.telemetry_logs);
      }

      if (data.saved_as_alternate) {
        setAlert({
          message: `🛡️ Existing README detected! Saved as alternate: ${data.output_filename} [${data.engine_mode}].`,
          type: 'warn',
        });
      } else if (data.was_overwritten) {
        setAlert({
          message: `⚠️ ${data.output_filename} was overwritten via the authorized --force setting [${data.engine_mode}].`,
          type: 'warn',
        });
      } else {
        setAlert({
          message: `🎉 Success! Documentation generated at ${data.output_filename} (${data.entities_documented_count} components documented) via ${data.engine_mode}.`,
          type: 'success',
        });
      }

      // Smooth scroll to preview
      setTimeout(() => {
        previewCardRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err: any) {
      setAlert({ message: `Client request failure: ${err.message}`, type: 'error' });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!result?.session_id) return;
    window.location.href = `/api/download?session_id=${encodeURIComponent(result.session_id)}`;
  };

  const handleCopy = () => {
    if (!result?.markdown_content) return;
    navigator.clipboard.writeText(result.markdown_content).then(() => {
      setAlert({ message: '📋 Markdown copied to clipboard!', type: 'success' });
    });
  };

  return (
    <div>
      {/* Top Header */}
      <header>
        <div className="brand">
          <div className="brand-icon">🤖</div>
          <div>
            <h1>README Writer Agent</h1>
            <p>React + FastAPI Architecture • Cloud & Vercel Ready</p>
          </div>
        </div>
        <div className="header-badges">
          <span className="badge badge-green">
            <ShieldCheck size={14} /> Security Guardrails Active
          </span>
          <span className="badge badge-purple">▲ Vercel Serverless Ready</span>
        </div>
      </header>

      <div className="container">
        {/* Configuration Card */}
        <div className="card">
          <div className="card-title">📁 Choose Source Mode</div>

          {/* Source Tabs */}
          <div className="mode-tabs">
            <button
              className={`mode-tab-btn ${mode === 'github' ? 'active' : ''}`}
              onClick={() => setMode('github')}
            >
              <GithubIcon size={15} style={{ verticalAlign: 'middle', marginRight: 6 }} />
              GitHub URL (Recommended for Vercel)
            </button>
            <button
              className={`mode-tab-btn ${mode === 'zip' ? 'active' : ''}`}
              onClick={() => setMode('zip')}
            >
              <FolderArchive size={15} style={{ verticalAlign: 'middle', marginRight: 6 }} />
              Upload Project (.zip)
            </button>
            <button
              className={`mode-tab-btn ${mode === 'local' ? 'active' : ''}`}
              onClick={() => setMode('local')}
            >
              <HardDrive size={15} style={{ verticalAlign: 'middle', marginRight: 6 }} />
              Local Filesystem Path
            </button>
          </div>

          {/* Mode 1: GitHub URL */}
          {mode === 'github' && (
            <div className="form-group">
              <label htmlFor="githubUrl">Public GitHub Repository URL</label>
              <input
                type="text"
                id="githubUrl"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/Abhijit2244/readme-writer-agent"
              />
              <div className="quick-chips">
                <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center' }}>Quick Test:</span>
                <span
                  className="chip"
                  onClick={() => setGithubUrl('https://github.com/Abhijit2244/readme-writer-agent')}
                >
                  Abhijit2244/readme-writer-agent
                </span>
              </div>
            </div>
          )}

          {/* Mode 2: Zip Upload */}
          {mode === 'zip' && (
            <div className="form-group">
              <label htmlFor="zipFile">Select Project Zip Archive (.zip)</label>
              <input
                type="file"
                id="zipFile"
                accept=".zip"
                onChange={(e) => setZipFile(e.target.files ? e.target.files[0] : null)}
              />
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Safe archive extraction with automated Zip-Slip path traversal defense.
              </p>
            </div>
          )}

          {/* Mode 3: Local Filesystem Path */}
          {mode === 'local' && (
            <div className="form-group">
              <label htmlFor="repoPath">Local Repository Filesystem Path</label>
              <input
                type="text"
                id="repoPath"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                placeholder="e.g. C:\Users\Username\Projects\my-project or /home/user/my-project"
              />
              <div
                style={{
                  background: 'rgba(210, 153, 34, 0.12)',
                  border: '1px solid rgba(210, 153, 34, 0.35)',
                  borderRadius: 8,
                  padding: '10px 14px',
                  marginTop: 10,
                  fontSize: 12,
                  color: '#e3b341',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                }}
              >
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                <span>
                  <strong>Cloud Notice:</strong> Local filesystem paths (e.g. <code>C:/Users/...</code>) only work
                  when running this server locally on your own machine. When hosted on cloud platforms like{' '}
                  <strong>Vercel</strong>, the server cannot access your personal device's files unless cloned
                  there—please use the <strong>🌐 GitHub URL</strong> or <strong>📦 Upload Project (.zip)</strong> tab!
                </span>
              </div>
            </div>
          )}

          {/* Engine Selector */}
          <div style={{ marginTop: 20, borderTop: '1px solid var(--card-border)', paddingTop: 16 }}>
            <label style={{ fontWeight: 600, fontSize: 13.5, color: '#f0f6fc', marginBottom: 8, display: 'block' }}>
              ⚡ Analysis & Synthesis Engine:
            </label>
            <div className="engine-toggle-group">
              <div
                className={`engine-btn ${engine === 'local' ? 'active' : ''}`}
                onClick={() => setEngine('local')}
              >
                <div className="engine-btn-title">
                  <Zap size={15} color="#3fb950" /> Local Deterministic AST Mode
                </div>
                <div className="engine-btn-sub">
                  100% Offline • Free & Instant • Zero API keys required • Direct Python AST extraction
                </div>
              </div>
              <div
                className={`engine-btn engine-gemini ${engine === 'gemini' ? 'active' : ''}`}
                onClick={() => setEngine('gemini')}
              >
                <div className="engine-btn-title">
                  <Sparkles size={15} color="#d2a8ff" /> Gemini 2.0 Flash AI Mode
                </div>
                <div className="engine-btn-sub">
                  Google Gemini AI • Enriches undocumented functions & synthesizes executive summaries
                </div>
              </div>
            </div>
          </div>

          {/* Guardrail Option Row */}
          <div className="options-row">
            <label className="toggle-label">
              <input
                type="checkbox"
                id="forceOverwrite"
                checked={forceOverwrite}
                onChange={(e) => setForceOverwrite(e.target.checked)}
              />
              <span>
                <strong>Allow Overwrite Existing README</strong> (<code>--force</code>)
              </span>
            </label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              🔒 Default preserves existing <code>README.md</code> ➔ writes to <code>README.generated.md</code>
            </span>
          </div>

          {/* Submit Action */}
          <div className="btn-row">
            <button className="btn-primary" onClick={handleGenerate} disabled={isGenerating}>
              {isGenerating && <span className="spinner"></span>}
              <span>⚡ Generate Production README</span>
            </button>
          </div>
        </div>

        {/* Dismissible Alert Banner */}
        {alert && (
          <div className={`alert-banner alert-${alert.type}`}>
            <div>{alert.message}</div>
            <button
              onClick={() => setAlert(null)}
              style={{ background: 'transparent', padding: 0, color: 'inherit' }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Live Telemetry Terminal */}
        {(isGenerating || telemetryLogs.length > 0) && (
          <div className="card">
            <div className="card-title">📡 Real-Time Telemetry & AST Extraction Logs</div>
            <div className="terminal-box">
              {telemetryLogs.map((log, index) => (
                <div key={index}>
                  [{log.type}] {typeof log.data === 'object' ? JSON.stringify(log.data) : log.data}
                </div>
              ))}
              <div ref={telemetryEndRef} />
            </div>
          </div>
        )}

        {/* Metrics Grid */}
        {result && (
          <div className="stats-grid">
            <div className="stat-card">
              <div
                className="stat-value"
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  lineHeight: 1.35,
                  padding: '0 4px',
                  color: result.engine_mode.includes('Gemini') ? '#d2a8ff' : '#7ee787',
                }}
              >
                {result.engine_mode.includes('Gemini') ? '✨ Gemini 2.0' : '⚡ Local AST'}
              </div>
              <div className="stat-label">Active Engine</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{result.sections_included.length}</div>
              <div className="stat-label">Sections Built</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{result.entities_documented_count}</div>
              <div className="stat-label">Classes & Functions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ fontSize: 18, fontWeight: 700 }}>
                {result.was_overwritten ? 'Overwritten' : result.saved_as_alternate ? 'Preserved' : 'Clean'}
              </div>
              <div className="stat-label">Safety Decision</div>
            </div>
            <div className="stat-card">
              <div
                className="stat-value stat-filename-pill"
                title={result.output_filename}
              >
                {result.output_filename}
              </div>
              <div className="stat-label">Target File</div>
            </div>
          </div>
        )}

        {/* Dual Tab Markdown Viewer */}
        {result && (
          <div className="card" ref={previewCardRef}>
            <div className="tab-header">
              <div className="tab-buttons">
                <button
                  className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
                  onClick={() => setActiveTab('preview')}
                >
                  <Eye size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                  Rendered HTML Preview
                </button>
                <button
                  className={`tab-btn ${activeTab === 'raw' ? 'active' : ''}`}
                  onClick={() => setActiveTab('raw')}
                >
                  <Code2 size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                  Raw Markdown
                </button>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn-secondary" onClick={handleCopy}>
                  <Copy size={14} /> Copy Markdown
                </button>
                <button className="btn-download" onClick={handleDownload}>
                  <Download size={14} /> Download {result.output_filename}
                </button>
              </div>
            </div>

            {/* Tab 1: Rendered View */}
            {activeTab === 'preview' && (
              <div
                className="markdown-body"
                id="markdownRenderedContainer"
                dangerouslySetInnerHTML={{ __html: marked.parse(result.markdown_content) as string }}
              />
            )}

            {/* Tab 2: Raw Markdown View */}
            {activeTab === 'raw' && (
              <textarea
                className="raw-textarea"
                value={result.markdown_content}
                readOnly
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
