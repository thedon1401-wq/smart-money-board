#!/usr/bin/env python3
"""Static site generator v2: data/data.json -> site/. Charts are inline SVG (no JS libs, no CDN)."""
import json, html, time, os, shutil, re, math
d=json.load(open("data/data.json")); E=html.escape
AFF="#AFFILIATE-LINK-PLACEHOLDER"  # TODO: replace with Polymarket referral URL
def usd(x):
    x=x or 0; s="-" if x<0 else ""; x=abs(x)
    return f"{s}${x/1e6:.1f}M" if x>=1e6 else f"{s}${x/1e3:.0f}K" if x>=1e3 else f"{s}${x:.0f}"
def pc(p): return f"{p*100:.0f}¢"
def mlink(slug,ev): return f"https://polymarket.com/event/{E(ev or slug or '')}"
CATS=[("Geopolitics",r"iran|israel|russia|ukraine|nato|china|taiwan|ceasefire|blockade|regime|netanyahu|war |military|strike"),
      ("Tech & AI",r"anthropic|openai|spacex|ipo|valuation|\bai\b|nvidia|apple|google|tesla|data center|aliens"),
      ("Politics",r"election|senate|house|president|trump|democrat|republican|governor|mayor|parliament|minister|balance of power|xi |putin|congress|vote|party|nominee"),
      ("Sports",r" win | vs\.? |premier league|epl|nba|nfl|mlb|nhl|champions|world cup|super bowl|finals|open|grand prix|ufc|fc |league|cup"),
      ("Crypto",r"bitcoin|btc|eth|ethereum|solana|crypto|token|coin|xrp|doge"),
      ("Economy",r"fed |rate|inflation|cpi|gdp|recession|tariff|stock|s&p|nasdaq")]
COL={"Politics":"#7c9cff","Sports":"#5fe3a1","Crypto":"#ffb547","Economy":"#e879f9","Geopolitics":"#f87171","Tech & AI":"#38bdf8","Other":"#64748b"}
def cat(t):
    t=" "+t.lower()+" "
    for n,r in CATS:
        if re.search(r,t): return n
    return "Other"
def side(o): o=o.lower(); return "yes" if o=="yes" else "no" if o=="no" else "oth"
# ---------- SVG charts ----------
def donut(parts):
    tot=sum(v for _,v in parts) or 1; r=60; c=2*math.pi*r; off=0; segs=""
    for n,v in parts:
        l=c*v/tot; segs+=f'<circle r="{r}" cx="80" cy="80" fill="none" stroke="{COL[n]}" stroke-width="26" stroke-dasharray="{l:.1f} {c-l:.1f}" stroke-dashoffset="{-off:.1f}" transform="rotate(-90 80 80)"/>'; off+=l
    leg="".join(f'<li><i style="background:{COL[n]}"></i>{n}<b>{v/tot*100:.0f}%</b></li>' for n,v in parts)
    return f'<div class="donut"><svg viewBox="0 0 160 160" width="160" height="160">{segs}<text x="80" y="76" text-anchor="middle" class="dt">{usd(tot)}</text><text x="80" y="96" text-anchor="middle" class="ds">open value</text></svg><ul class="leg">{leg}</ul></div>'
def hbars(items,color="#5fe3a1"):
    mx=max((v for _,v,_ in items),default=1) or 1
    return '<div class="hb">'+"".join(f'<div class="hbr"><span class="hbl">{lbl}</span><span class="hbt"><span style="width:{max(2,v/mx*100):.1f}%;background:{color}"></span></span><span class="hbv">{val}</span></div>' for lbl,v,val in items)+'</div>'
def split(forv,agv):
    t=(forv+agv) or 1; return f'<div class="split" title="for vs against"><span class="sf" style="width:{forv/t*100:.1f}%"></span><span class="sa" style="width:{agv/t*100:.1f}%"></span></div>'
def gauge(avg,cur):
    # price track 0-100¢: hollow dot = avg entry, solid = now
    a,c_=avg*100,cur*100; lo,hi=sorted((a,c_)); up=c_>=a
    return f'<div class="gauge"><span class="gl" style="left:{lo:.1f}%;width:{hi-lo:.1f}%;background:{"#5fe3a1" if up else "#ff6b7a"}"></span><span class="ge" style="left:{a:.1f}%"></span><span class="gc" style="left:{c_:.1f}%"></span></div>'
# ---------- data prep ----------
board=d["board"]; cons=d["consensus"]
catv={}
for b in board:
    for p in b["positions"]: k=cat(p["title"]); catv[k]=catv.get(k,0)+p["currentValue"]
catparts=sorted(catv.items(),key=lambda x:-x[1])
total_open=sum(b["open_value"] for b in board); active=sum(1 for b in board if b["n_open"])
ts=time.strftime("%b %d, %Y · %H:%M UTC",time.gmtime(d["generated"]))
pnl_chart=hbars([(E(b["name"][:16]),b["pnl"],usd(b["pnl"])) for b in board[:10]])
cons_chart=hbars([(E(c["title"][:34]+("…" if len(c["title"])>34 else ""))+f' <em class="{side(c["outcome"])}">{E(c["outcome"])}</em>',c["value"],usd(c["value"])) for c in cons[:8]],"#7c9cff")
# ---------- sections ----------
cards=""
for c in cons[:9]:
    avg=sum(h["avg"]*h["value"] for h in c["holders"])/(sum(h["value"] for h in c["holders"]) or 1)
    names=", ".join(f'<a href="#w-{h["wallet"]}">{E(h["name"])}</a>' for h in c["holders"][:5])
    cards+=f'''<article class="card"><div class="row"><span class="chip c-{cat(c["title"]).lower().split()[0]}">{cat(c["title"])}</span><span class="cnt">{c["n"]} wallets</span></div>
<h3><a href="{mlink(c["slug"],c["eventSlug"])}" target="_blank" rel="noopener">{E(c["title"])}</a></h3>
<div class="big"><span class="pill {side(c["outcome"])}">{E(c["outcome"])}</span><span class="price">{pc(c["curPrice"])}</span><span class="amt">{usd(c["value"])} in</span></div>
{split(c["value"],c.get("against_value",0))}<div class="row small muted"><span>For {usd(c["value"])}</span><span>{f'Against {usd(c["against_value"])}' if c["against"] else "No top wallet against"}</span></div>
{gauge(avg,c["curPrice"])}<div class="row small muted"><span>◯ avg entry {pc(avg)}</span><span>● now {pc(c["curPrice"])}</span></div>
<details class="more"><summary>Details</summary><p class="small muted">Held by {names}<br>Market volume {usd(c.get("volume"))} · ends {(c["endDate"] or "")[:10]}</p></details>
<a class="cta" href="{AFF}" data-placeholder="affiliate">Trade on Polymarket →</a></article>'''
wl=""
for b in board:
    mx=max((p["currentValue"] for p in b["positions"]),default=1)
    pos="".join(f'''<div class="pos"><a class="pt" href="{mlink(p["slug"],p["eventSlug"])}" target="_blank" rel="noopener">{E(p["title"])}</a>
<div class="row"><span class="pill {side(p["outcome"])}">{E(p["outcome"])}</span><span class="small muted">{pc(p["avgPrice"])} → {pc(p["curPrice"])}</span><span class="pv">{usd(p["currentValue"])}</span><span class="{"up" if p["cashPnl"]>=0 else "dn"} small">{"+" if p["cashPnl"]>=0 else ""}{usd(p["cashPnl"])}</span></div>{gauge(p["avgPrice"],p["curPrice"])}</div>''' for p in b["positions"][:8]) or '<p class="muted small">No open positions above threshold — likely cashed out.</p>'
    lt=time.strftime("%b %d",time.gmtime(b["last_trade"])) if b["last_trade"] else "—"
    wl+=f'''<details class="w" id="w-{b["wallet"]}" data-name="{E(b["name"].lower())}"><summary><span class="rk">{b["rank"]}</span><span class="nm">{E(b["name"])}<small>{b["n_open"]} open · {usd(b["open_value"])} · last trade {lt}</small></span><span class="pnl">{usd(b["pnl"])}</span><span class="chev">›</span></summary>
<div class="pl">{pos}<a class="small" href="https://polymarket.com/profile/{b["wallet"]}" target="_blank" rel="noopener">Full profile on Polymarket ↗</a></div></details>'''
mov="".join(f'<li><span class="rk">{m["rank"]}</span><a href="https://polymarket.com/profile/{m["wallet"]}" target="_blank" rel="noopener">{E(m["name"])}</a>{"" if m["in_month_pool"] else "<span class=new>NEW</span>"}<span class="{"up" if m["pnl"]>=0 else "dn"}">{usd(m["pnl"])}</span></li>' for m in d["weekly_movers"][:8])
page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Money Board – What Polymarket's top wallets are betting on right now</title>
<meta name="description" content="Consensus bets of the most profitable Polymarket wallets, weekly movers and open positions.">
<link rel="stylesheet" href="style.css"></head><body>
<nav class="top"><div class="wrap nav"><a class="logo" href="#">◆ Smart Money</a><div class="links"><a href="#consensus">Consensus</a><a href="#movers">Movers</a><a href="#board">Wallets</a><a class="sub" href="#newsletter">Subscribe</a></div></div></nav>
<header class="wrap hero"><p class="eyebrow">Updated {ts}</p><h1>What Polymarket's top wallets are betting on <em>right now</em></h1>
<p class="lede">We track the {d["pool"]} most profitable wallets of the last 30 days and surface where they agree.</p>
<div class="kpis"><div><b>{len(cons)}</b><span>consensus bets</span></div><div><b>{usd(total_open)}</b><span>smart money open</span></div><div><b>{active}/{d["pool"]}</b><span>wallets active</span></div></div></header>
<main class="wrap">
<div class="sponsor" data-placeholder="sponsor">SPONSOR BANNER PLACEHOLDER · 728×90 · <a href="mailto:SPONSOR-CONTACT-PLACEHOLDER">Advertise here</a></div>
<section id="consensus"><div class="sh"><h2>Consensus bets</h2><p class="muted">Same market, same side, held by 3+ top wallets (≥ ${d["min_pos"]:.0f} each).</p></div>
<div class="panel"><h4>Smart money by consensus bet</h4>{cons_chart}</div>
<div class="grid">{cards or '<p class="muted">No consensus right now.</p>'}</div></section>
<section class="charts"><div class="panel"><h4>Where top wallets have money</h4>{donut(catparts)}</div><div class="panel"><h4>30-day P&amp;L · top 10</h4>{pnl_chart}</div></section>
<section id="movers" class="split2"><div class="panel"><div class="sh"><h2>Weekly movers</h2><p class="muted small">7-day P&amp;L. <span class="new">NEW</span> = outside the 30-day top {d["pool"]}.</p></div><ol class="mov">{mov}</ol></div>
<div id="newsletter" class="panel nl"><h2>The Sunday Smart Money Brief</h2><p class="muted">One email a week: biggest consensus bets, new whales, notable exits. Free.</p>
<form id="nlf"><input type="email" required placeholder="you@email.com" aria-label="Email"><button>Subscribe</button></form><p id="nlmsg" class="small muted">Placeholder form — not connected to a newsletter service yet.</p></div></section>
<section id="board"><div class="sh"><h2>Wallet leaderboard</h2><p class="muted">Ranked by 30-day P&amp;L. Tap a wallet to see open positions.</p></div><input id="q" placeholder="Search wallets…" aria-label="Search wallets"><div class="list">{wl}</div></section>
<div class="sponsor" data-placeholder="sponsor">SPONSOR BANNER PLACEHOLDER · native slot</div>
<a href="{AFF}" data-placeholder="affiliate" class="cta wide">New to Polymarket? Sign up here (AFFILIATE LINK PLACEHOLDER)</a>
</main><footer class="wrap small muted">Data: Polymarket public APIs. Not financial advice. Past performance ≠ future results. Not affiliated with Polymarket.</footer>
<script>
document.getElementById('q').oninput=e=>{{const v=e.target.value.toLowerCase();document.querySelectorAll('.w').forEach(w=>w.style.display=w.dataset.name.includes(v)?'':'none')}};
document.getElementById('nlf').onsubmit=e=>{{e.preventDefault();document.getElementById('nlmsg').textContent='Thanks! (demo only — nothing was sent or stored)';e.target.reset()}};
</script></body></html>'''
css='''*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}
body{margin:0;background:#0a0d14;color:#e8ebf2;font:16px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
a{color:#8ab4ff;text-decoration:none}.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
.muted{color:#8b93a7}.small{font-size:13px}h1,h2,h3,h4{letter-spacing:-.02em;margin:0}
.top{position:sticky;top:0;z-index:10;background:rgba(10,13,20,.85);backdrop-filter:blur(10px);border-bottom:1px solid #1a2030}
.nav{display:flex;align-items:center;justify-content:space-between;height:60px}.logo{font-weight:800;color:#5fe3a1;white-space:nowrap}
.links{display:flex;gap:4px}.links a{color:#c3cad8;padding:10px 12px;border-radius:10px;font-size:14px}.links a:hover{background:#151b29}.links .sub{background:#5fe3a1;color:#06200f;font-weight:700}
.hero{padding:64px 20px 40px}.eyebrow{color:#5fe3a1;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin:0 0 12px}
h1{font-size:clamp(30px,5.5vw,52px);line-height:1.08;max-width:780px}h1 em{color:#5fe3a1;font-style:normal}
.lede{color:#a3abbd;font-size:18px;max-width:600px;margin:18px 0 32px}
.kpis{display:flex;gap:40px;flex-wrap:wrap}.kpis b{display:block;font-size:28px;font-weight:800}.kpis span{color:#8b93a7;font-size:13px}
section{margin:72px 0}.sh{margin-bottom:24px}h2{font-size:26px;margin-bottom:6px}h4{font-size:14px;color:#a3abbd;font-weight:600;margin-bottom:18px}
.panel{background:#10141f;border:1px solid #1a2030;border-radius:18px;padding:24px}
.sponsor{border:2px dashed #e0b84a;color:#e0b84a;text-align:center;padding:22px;border-radius:14px;margin:40px 0;font-weight:600;background:#17140a;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin-top:20px}
.card{background:#10141f;border:1px solid #1a2030;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:12px}
.card h3{font-size:17px;line-height:1.35}.card h3 a{color:#fff}.row{display:flex;justify-content:space-between;align-items:center;gap:10px}
.chip{font-size:11px;font-weight:700;padding:3px 9px;border-radius:99px;text-transform:uppercase;letter-spacing:.05em}
.c-politics{background:#1b2347;color:#9fb4ff}.c-sports{background:#0f2e22;color:#5fe3a1}.c-crypto{background:#33260d;color:#ffc56b}.c-economy{background:#2e1438;color:#f0a6ff}.c-geopolitics{background:#3a1717;color:#fca5a5}.c-tech{background:#0c2a3a;color:#7dd3fc}.c-other{background:#1c2230;color:#9aa4b8}
.cnt{font-size:13px;color:#8b93a7}.big{display:flex;align-items:baseline;gap:10px}.price{font-size:28px;font-weight:800}.amt{color:#8b93a7;margin-left:auto;font-weight:600}
.pill{padding:3px 10px;border-radius:7px;font-weight:700;font-size:13px}.yes{background:#0f3324;color:#5fe3a1}.no{background:#3a1419;color:#ff7b86}.oth{background:#1f2a45;color:#9fc2ff}
em.yes,em.no,em.oth{font-style:normal;background:none;font-weight:700}
.split{display:flex;height:8px;border-radius:99px;overflow:hidden;background:#1a2030}.sf{background:#5fe3a1}.sa{background:#ff6b7a}
.gauge{position:relative;height:6px;background:#1a2030;border-radius:99px;margin:6px 0 2px}.gl{position:absolute;top:0;height:6px;border-radius:99px;opacity:.7}
.ge,.gc{position:absolute;top:50%;width:12px;height:12px;border-radius:50%;transform:translate(-50%,-50%)}.ge{border:2px solid #c3cad8;background:#0a0d14}.gc{background:#fff}
details.more summary{cursor:pointer;color:#8b93a7;font-size:13px;list-style:none}details.more summary::before{content:"+ "}details.more[open] summary::before{content:"– "}
.cta{margin-top:auto;display:block;text-align:center;border:1px dashed #8ab4ff;border-radius:12px;padding:12px;font-weight:600;min-height:44px}.cta.wide{padding:20px;margin:40px 0}
.charts,.split2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.donut{display:flex;align-items:center;gap:24px;flex-wrap:wrap}.dt{fill:#fff;font-weight:800;font-size:18px}.ds{fill:#8b93a7;font-size:11px}
.leg{list-style:none;padding:0;margin:0;flex:1;min-width:140px}.leg li{display:flex;align-items:center;gap:10px;padding:5px 0;font-size:14px}.leg i{width:10px;height:10px;border-radius:3px}.leg b{margin-left:auto}
.hb{display:flex;flex-direction:column;gap:10px}.hbr{display:grid;grid-template-columns:minmax(0,1.4fr) 2fr auto;gap:12px;align-items:center;font-size:13px}
.hbl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#c3cad8}.hbt{height:10px;background:#1a2030;border-radius:99px;overflow:hidden}.hbt span{display:block;height:100%;border-radius:99px}.hbv{font-weight:700;min-width:56px;text-align:right}
.mov{list-style:none;padding:0;margin:0}.mov li{display:flex;gap:12px;align-items:center;padding:12px 0;border-bottom:1px solid #1a2030}.mov li>span:last-child{margin-left:auto;font-weight:700}
.rk{color:#5d667a;font-weight:700;min-width:24px;font-variant-numeric:tabular-nums}.up{color:#5fe3a1}.dn{color:#ff7b86}
.new{background:#4b32d9;color:#fff;font-size:10px;padding:2px 6px;border-radius:5px;font-weight:700}
.nl{background:linear-gradient(140deg,#12233f,#1a1236);border-color:#26305a}.nl h2{font-size:22px}
form{display:flex;gap:10px;margin-top:18px}input{flex:1;min-width:0;background:#0a0d14;border:1px solid #2a3350;color:#fff;padding:14px;border-radius:12px;font-size:16px}
button{background:#5fe3a1;color:#06200f;border:0;font-weight:800;padding:0 22px;border-radius:12px;cursor:pointer;min-height:48px;font-size:15px}
#q{width:100%;margin-bottom:16px}.list{display:flex;flex-direction:column;gap:10px}
.w{background:#10141f;border:1px solid #1a2030;border-radius:16px}.w summary{display:flex;gap:16px;align-items:center;padding:18px 20px;cursor:pointer;list-style:none;min-height:64px}
.w summary::-webkit-details-marker{display:none}.nm{font-weight:700;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}.nm small{display:block;color:#8b93a7;font-weight:400;font-size:13px}
.pnl{font-weight:800;color:#5fe3a1;font-size:17px}.chev{color:#5d667a;font-size:22px;transition:.2s}.w[open] .chev{transform:rotate(90deg)}
.pl{padding:0 20px 20px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}.pl>a{grid-column:1/-1}
.pos{background:#0c1019;border:1px solid #1a2030;border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px}.pt{color:#e8ebf2;font-size:14px;font-weight:600;line-height:1.35}.pv{margin-left:auto;font-weight:700}
footer{padding:40px 20px 60px;border-top:1px solid #1a2030;margin-top:40px}
@media(max-width:760px){body{font-size:15px}.logo{font-size:15px}.links a.sub{padding:8px 12px}.hero{padding:40px 20px 24px}.links a:not(.sub){padding:10px 8px;font-size:13px}.links a[href="#movers"]{display:none}
section{margin:52px 0}.charts,.split2{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.kpis{gap:24px}.kpis b{font-size:22px}
.panel,.card{padding:18px;border-radius:16px}.hbr{grid-template-columns:minmax(0,1fr) 1fr auto}.pl{grid-template-columns:1fr;padding:0 14px 14px}.w summary{padding:16px}form{flex-direction:column}}'''
os.makedirs("site",exist_ok=True); open("site/index.html","w").write(page); open("site/style.css","w").write(css); shutil.copy("data/data.json","site/data.json")
print("built site/", dict(catparts))
