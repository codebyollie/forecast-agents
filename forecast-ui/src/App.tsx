import { useState, useEffect, useRef } from 'react';
import './index.css';

interface Evidence {
  source: string;
  title?: string;
  content: string;
  url?: string;
  time: string;
  score: number;
}

interface AgentForecast {
  name: string;
  probability: number;
  confidence: number;
  reasoning: string;
  status: 'active' | 'idle';
}

interface Market {
  id: string;
  question: string;
  slug: string;
  category: string;
  volume: number;
  liquidity: number;
  consensusProb: number;
  confidence: number;
  agents: AgentForecast[];
  evidence: Evidence[];
}

function App() {
  const [loading, setLoading] = useState(true);
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Preloader Logic
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 3500);
    return () => clearTimeout(timer);
  }, []);

  // Set up mock Polymarket data
  useEffect(() => {
    const mockMarkets: Market[] = [
      {
        id: "pm_btc_200k",
        question: "Will Bitcoin reach $200,000 in 2026?",
        slug: "will-bitcoin-reach-200k-in-2026",
        category: "Crypto",
        volume: 12543209,
        liquidity: 4500000,
        consensusProb: 0.68,
        confidence: 0.82,
        agents: [
          { name: "News Agent", probability: 0.72, confidence: 0.85, reasoning: "Positive macroeconomic outlook and SEC approval of options on spot BTC ETFs.", status: "active" },
          { name: "Social Agent", probability: 0.65, confidence: 0.75, reasoning: "High retail hype across X and Reddit, though cooling slightly after local peaks.", status: "active" },
          { name: "Research Agent", probability: 0.70, confidence: 0.90, reasoning: "Long-term stock-to-flow models and halving supply shock projections align with this range.", status: "active" },
          { name: "Macro Agent", probability: 0.60, confidence: 0.80, reasoning: "Fed rate cut cycle continuing, boosting liquidity flows into risk assets.", status: "active" },
          { name: "On-chain Agent", probability: 0.74, confidence: 0.88, reasoning: "Heavy whale accumulation and declining exchange balances support bullish trend.", status: "active" },
          { name: "Market Agent", probability: 0.67, confidence: 0.92, reasoning: "CLOB order book shows strong bid support at $95k; long futures premium is expanding.", status: "active" }
        ],
        evidence: [
          { source: "news", title: "Global Liquidity Index Hits Record High", content: "M2 money supply expansion from major central banks accelerates, feeding digital asset markets.", time: "10m ago", score: 0.9 },
          { source: "blockchain", content: "Whale Wallet 0x72a transfers 4,200 BTC off Coinbase into cold storage.", time: "1h ago", score: 0.88 },
          { source: "twitter", content: "@MacroAnalyst: Fed dot plot signals two more rate cuts this year. Bullish for BTC.", time: "2h ago", score: 0.75 },
          { source: "reddit", content: "r/Bitcoin: Institutional inflows into ETFs reach $1.2B in single week.", time: "4h ago", score: 0.7 }
        ]
      },
      {
        id: "pm_fed_cut",
        question: "Will the Federal Reserve cut interest rates in September?",
        slug: "will-fed-cut-september",
        category: "Macro",
        volume: 8432109,
        liquidity: 3200000,
        consensusProb: 0.84,
        confidence: 0.89,
        agents: [
          { name: "News Agent", probability: 0.85, confidence: 0.90, reasoning: "Leading WSJ articles and Fed whispers suggest 25bps cut is locked in.", status: "active" },
          { name: "Research Agent", probability: 0.82, confidence: 0.92, reasoning: "Core inflation dropping to 2.4% matches Fed's price stability goals.", status: "active" },
          { name: "Macro Agent", probability: 0.88, confidence: 0.95, reasoning: "Labor market cooling indices indicate economic pain if rates stay high.", status: "active" },
          { name: "Market Agent", probability: 0.81, confidence: 0.91, reasoning: "CME FedWatch tool pricing in 94% chance of rate cuts; treasury yields falling.", status: "active" }
        ],
        evidence: [
          { source: "news", title: "US CPI Index drops to 2.4% annually", content: "Inflation metrics continue steady downward path toward the Federal Reserve's target.", time: "15m ago", score: 0.95 },
          { source: "rss", title: "FT: Bond Yields Fall on Monetary Easing Hopes", content: "Treasury yields drop across maturities as traders position for rate cuts.", time: "30m ago", score: 0.85 },
          { source: "twitter", content: "@EconomicsFeed: Fed governor says labor market balance is restored. Rate cut ready.", time: "3h ago", score: 0.8 }
        ]
      },
      {
        id: "pm_eth_merge",
        question: "Will Ethereum gas fee average stay below 20 Gwei in Q3?",
        slug: "eth-gas-below-20-gwei",
        category: "Crypto",
        volume: 3209843,
        liquidity: 1100000,
        consensusProb: 0.45,
        confidence: 0.78,
        agents: [
          { name: "On-chain Agent", probability: 0.40, confidence: 0.85, reasoning: "L2 transactions growing by 300% taking pressure off Ethereum L1 base fees.", status: "active" },
          { name: "Market Agent", probability: 0.50, confidence: 0.80, reasoning: "Speculative token trading volume is rising, which usually spikes base fees.", status: "active" }
        ],
        evidence: [
          { source: "blockchain", content: "Average Base Fee: 12 Gwei. Blob space saturation: 32%. L2 volume ratio: 84%.", time: "5m ago", score: 0.92 },
          { source: "news", title: "L2 adoption scales to new record", content: "Arbitrum and Base process over 150 transactions per second combined.", time: "2h ago", score: 0.8 }
        ]
      }
    ];

    setMarkets(mockMarkets);
    setSelectedMarket(mockMarkets[0]);
  }, []);

  // Simulated live event logger for terminal
  useEffect(() => {
    if (loading || !selectedMarket) return;

    const addLog = (text: string) => {
      setLogs(prev => [...prev.slice(-29), `[${new Date().toLocaleTimeString()}] ${text}`]);
    };

    addLog(`INIT: Forecast AI Intelligence Pipeline loaded.`);
    addLog(`POLL: Connecting to Polymarket Gamma API...`);
    addLog(`SUCCESS: Found ${markets.length} active tracked markets.`);
    addLog(`TARGET: Streaming orderbook for ${selectedMarket.question}`);

    const interval = setInterval(() => {
      const activities = [
        `TICKER: CLOB price tick for ${selectedMarket.id} -> ${selectedMarket.consensusProb + (Math.random() - 0.5) * 0.02}`,
        `EVIDENCE: Parsing new RSS headline: "Market volatility contracts." Relevance: 0.81`,
        `AGENT_RUN: News Agent recalculating consensus probability...`,
        `CALIBRATION: Probability calibration complete. Final consensus updated.`,
        `DATABASE: Writing forecast record to MemoryStore: ${selectedMarket.id}`,
        `WS_FEED: Received heartbeat from Polymarket matching engine.`
      ];
      addLog(activities[Math.floor(Math.random() * activities.length)]);
    }, 5000);

    return () => clearInterval(interval);
  }, [loading, selectedMarket, markets]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <>
      {/* PRELOADER */}
      <div className={`loading-screen ${!loading ? 'hidden' : ''}`}>
        <div className="loader-container">
          <div className="loader-ring"></div>
          <div className="loader-ring-inner"></div>
          <div className="loader-icon">🔮</div>
        </div>
        <div className="loading-text-container">
          <div className="loading-title">Forecast AI</div>
          <div className="loading-subtitle">Prediction Market Intelligence Layer</div>
          <div className="progress-bar-container">
            <div className="progress-bar"></div>
          </div>
        </div>
      </div>

      {/* DASHBOARD LAYOUT */}
      {!loading && selectedMarket && (
        <div className="dashboard-container">
          <header className="top-nav">
            <div className="brand">
              <div className="brand-icon">🔮</div>
              <div className="brand-text">
                <h1>Forecast AI</h1>
                <p>Open-Source Multi-Agent Intelligence Infrastructure for Prediction Markets</p>
              </div>
            </div>
            <nav className="nav-links">
              <span className="status-online" style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="status-dot"></span> LIVE POLYMARKET FEED
              </span>
            </nav>
          </header>

          <div className="grid-layout">
            
            {/* LEFT COLUMN: ACTIVE MARKET & FORECAST DETAILS */}
            <main style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Markets selection */}
              <div className="glass-panel" style={{ padding: '16px 24px' }}>
                <h2 className="panel-title">Tracked Markets</h2>
                <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px' }}>
                  {markets.map(m => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setSelectedMarket(m);
                        setLogs([]);
                      }}
                      style={{
                        background: selectedMarket.id === m.id ? 'rgba(255,255,255,0.08)' : 'transparent',
                        color: selectedMarket.id === m.id ? '#fff' : '#9aa0a6',
                        border: '1px solid ' + (selectedMarket.id === m.id ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)'),
                        padding: '10px 18px',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                        fontWeight: selectedMarket.id === m.id ? 'bold' : 'normal',
                        transition: 'all 0.2s'
                      }}
                    >
                      {m.category}: {m.question.length > 35 ? m.question.slice(0, 35) + "..." : m.question}
                    </button>
                  ))}
                </div>
              </div>

              {/* Forecast consensus card */}
              <div className="glass-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                  <div>
                    <span style={{ fontSize: '11px', textTransform: 'uppercase', color: '#9aa0a6', letterSpacing: '1px' }}>
                      Active Consensus Forecast
                    </span>
                    <h2 style={{ fontSize: '24px', fontWeight: '800', marginTop: '6px', marginBottom: '8px' }}>
                      {selectedMarket.question}
                    </h2>
                    <div style={{ display: 'flex', gap: '24px', fontSize: '13px', color: '#9aa0a6' }}>
                      <span>Volume: <strong>${selectedMarket.volume.toLocaleString()}</strong></span>
                      <span>Liquidity: <strong>${selectedMarket.liquidity.toLocaleString()}</strong></span>
                      <span>Category: <strong>{selectedMarket.category}</strong></span>
                    </div>
                  </div>
                  
                  {/* Circle charts or meters */}
                  <div style={{ display: 'flex', gap: '20px' }}>
                    <div style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)', padding: '16px 20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ fontSize: '32px', fontWeight: '800', color: '#fff' }}>
                        {(selectedMarket.consensusProb * 100).toFixed(0)}%
                      </div>
                      <div style={{ fontSize: '10px', color: '#9aa0a6', letterSpacing: '1px', textTransform: 'uppercase', marginTop: '4px' }}>
                        Probability
                      </div>
                    </div>
                    <div style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)', padding: '16px 20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ fontSize: '32px', fontWeight: '800', color: '#fff' }}>
                        {(selectedMarket.confidence * 100).toFixed(0)}%
                      </div>
                      <div style={{ fontSize: '10px', color: '#9aa0a6', letterSpacing: '1px', textTransform: 'uppercase', marginTop: '4px' }}>
                        Confidence
                      </div>
                    </div>
                  </div>
                </div>

                {/* Consensus Breakdown Progress Bars */}
                <div style={{ marginTop: '32px' }}>
                  <h3 className="panel-title" style={{ marginBottom: '16px' }}>Consensus Breakdown</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    {selectedMarket.agents.map(a => (
                      <div key={a.name} style={{ background: 'rgba(255,255,255,0.01)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '8px' }}>
                          <span style={{ fontWeight: '600' }}>{a.name}</span>
                          <span style={{ color: '#fff' }}>{(a.probability * 100).toFixed(0)}% (Conf: {(a.confidence * 100).toFixed(0)}%)</span>
                        </div>
                        <div style={{ height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ width: `${a.probability * 100}%`, height: '100%', background: '#fff' }}></div>
                        </div>
                        <p style={{ fontSize: '11px', color: '#9aa0a6', marginTop: '8px', lineHeight: '1.4' }}>
                          {a.reasoning}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Evidence list */}
              <div className="glass-panel">
                <h2 className="panel-title">Evidence Feed</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {selectedMarket.evidence.map((ev, i) => (
                    <div key={i} style={{ display: 'flex', gap: '16px', padding: '16px', borderRadius: '12px', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)' }}>
                      <div style={{
                        width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', flexShrink: 0
                      }}>
                        {ev.source === 'news' ? '📰' : ev.source === 'blockchain' ? '⛓' : ev.source === 'reddit' ? '👽' : '🐦'}
                      </div>
                      <div style={{ flexGrow: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}>{ev.source}</span>
                          <span style={{ fontSize: '11px', color: '#9aa0a6' }}>{ev.time}</span>
                        </div>
                        {ev.title && <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>{ev.title}</h4>}
                        <p style={{ fontSize: '13px', color: '#9aa0a6', lineHeight: '1.5' }}>{ev.content}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </main>

            {/* RIGHT COLUMN: TERMINAL & SYSTEM METRICS */}
            <aside style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '380px', padding: '2px', overflow: 'hidden' }}>
                <div style={{ padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <h2 className="panel-title" style={{ margin: 0 }}>Intelligence Stream</h2>
                </div>
                <div className="terminal-window" style={{ flexGrow: 1, padding: '16px 20px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '11px', color: '#9aa0a6' }}>
                  {logs.map((log, i) => (
                    <div key={i} style={{ marginBottom: '6px', lineHeight: '1.4' }}>
                      {log}
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              </div>

              <div className="glass-panel">
                <h2 className="panel-title">System Metrics</h2>
                <div className="stat-grid">
                  <div className="stat-card">
                    <span className="stat-label">Calibration Mode</span>
                    <span className="stat-value" style={{ color: '#fff' }}>BAYESIAN</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Active Agents</span>
                    <span className="stat-value" style={{ color: '#fff' }}>{selectedMarket.agents.length}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Evidence Score</span>
                    <span className="stat-value" style={{ color: '#fff' }}>0.86</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Aggregator</span>
                    <span className="stat-value" style={{ color: '#fff' }}>WEIGHTED</span>
                  </div>
                </div>
              </div>

              <div className="glass-panel">
                <h2 className="panel-title">Forecast AI Integration</h2>
                <div style={{ fontSize: '13px', color: '#9aa0a6', lineHeight: '1.6' }}>
                  <p style={{ marginBottom: '12px' }}>
                    <strong style={{color:'#fff'}}>Gamma discovery</strong><br/>
                    Polls market metadata, token IDs, and outcome structures directly from Polymarket's Gamma APIs.
                  </p>
                  <p style={{ marginBottom: '12px' }}>
                    <strong style={{color:'#fff'}}>Multi-agent analysis</strong><br/>
                    Spawns specialized agents to evaluate social dynamics, order books, and macroeconomics.
                  </p>
                  <p>
                    <strong style={{color:'#fff'}}>Consensus engine</strong><br/>
                    Applies Bayesian calibrations and reputation weight adjustments to produce explainable forecasts.
                  </p>
                </div>
              </div>

            </aside>
          </div>

          <footer className="footer" style={{ borderTop: '1px solid var(--surface-border)', marginTop: '60px', padding: '24px 0', textAlign: 'center', fontSize: '12px', color: '#9aa0a6' }}>
            <p>FORECAST AI INTELLIGENCE GATEWAY. ALL SYSTEMS OPERATIONAL.</p>
          </footer>
        </div>
      )}
    </>
  );
}

export default App;
