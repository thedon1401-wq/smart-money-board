#!/usr/bin/env python3
"""Pull real Polymarket public data -> data/data.json. No API key needed."""
import json, time, urllib.request, urllib.parse, concurrent.futures as cf, os
DATA="https://data-api.polymarket.com"; GAMMA="https://gamma-api.polymarket.com"
POOL=int(os.environ.get("POOL",50)); MIN_POS=float(os.environ.get("MIN_POS",500)); MIN_WALLETS=3
def get(url, tries=3):
    for i in range(tries):
        try:
            r=urllib.request.Request(url,headers={"User-Agent":"smart-money-board/0.1"})
            return json.load(urllib.request.urlopen(r,timeout=30))
        except Exception as e:
            if i==tries-1: print("WARN",url,e); return []
            time.sleep(1.5*(i+1))
def lb(period,order="PNL",limit=50):
    return get(f"{DATA}/v1/leaderboard?timePeriod={period}&orderBy={order}&limit={limit}")
def positions(w):
    out=[]
    for off in (0,500):
        p=get(f"{DATA}/positions?user={w}&limit=500&offset={off}&sizeThreshold=1&sortBy=CURRENT")
        out+=p or []
        if len(p or [])<500: break
    return [x for x in out if x.get("currentValue",0)>=MIN_POS and not x.get("redeemable") and 0.01<x.get("curPrice",0)<0.99]
def last_trade(w):
    a=get(f"{DATA}/activity?user={w}&limit=1&type=TRADE"); return a[0]["timestamp"] if a else None
def main():
    month=lb("MONTH",limit=POOL); week=lb("WEEK",limit=25); alltime=lb("ALL",limit=25)
    wallets={w["proxyWallet"]:w for w in month}
    with cf.ThreadPoolExecutor(8) as ex:
        pos=dict(zip(wallets,ex.map(positions,wallets))); lt=dict(zip(wallets,ex.map(last_trade,wallets)))
    board=[]
    for w,m in wallets.items():
        ps=sorted(pos[w],key=lambda x:-x["currentValue"])
        board.append({"rank":int(m["rank"]),"wallet":w,"name":m.get("userName") or w[:8],"x":m.get("xUsername"),
          "pnl":m["pnl"],"vol":m["vol"],"open_value":sum(p["currentValue"] for p in ps),"n_open":len(ps),"last_trade":lt[w],
          "positions":[{k:p.get(k) for k in("title","slug","eventSlug","outcome","size","avgPrice","curPrice","currentValue","cashPnl","percentPnl","endDate","conditionId")} for p in ps[:15]]})
    board.sort(key=lambda b:b["rank"])
    # consensus: same market + same side held by >= MIN_WALLETS top wallets
    g={}
    for b in board:
        for p in pos[b["wallet"]]:
            k=(p["conditionId"],p["outcome"]); e=g.setdefault(k,{"conditionId":p["conditionId"],"title":p["title"],"slug":p.get("slug"),"eventSlug":p.get("eventSlug"),"outcome":p["outcome"],"curPrice":p["curPrice"],"endDate":p.get("endDate"),"holders":[],"value":0,"cost":0})
            e["holders"].append({"name":b["name"],"wallet":b["wallet"],"rank":b["rank"],"value":p["currentValue"],"avg":p["avgPrice"]}); e["value"]+=p["currentValue"]; e["cost"]+=p["avgPrice"]*p["size"]
    cons=[]
    for (cid,out),e in g.items():
        if len(e["holders"])<MIN_WALLETS: continue
        opp=[h for (c2,o2),e2 in g.items() if c2==cid and o2!=out for h in e2["holders"]]
        e["n"]=len(e["holders"]); e["against"]=len(opp); e["against_value"]=sum(h["value"] for h in opp)
        e["holders"].sort(key=lambda h:-h["value"]); cons.append(e)
    cons.sort(key=lambda e:(-e["n"],-e["value"]))
    # enrich with gamma market data
    cids=list({e["conditionId"] for e in cons})[:100]
    for i in range(0,len(cids),20):
        q="&".join("condition_ids="+c for c in cids[i:i+20])
        for m in get(f"{GAMMA}/markets?{q}&limit=50") or []:
            for e in cons:
                if e["conditionId"]==m.get("conditionId"): e["volume"]=float(m.get("volume") or 0); e["liquidity"]=float(m.get("liquidity") or 0); e["question"]=m.get("question")
    movers=[{"rank":int(w["rank"]),"wallet":w["proxyWallet"],"name":w.get("userName") or w["proxyWallet"][:8],"pnl":w["pnl"],"vol":w["vol"],"in_month_pool":w["proxyWallet"] in wallets} for w in week]
    out={"generated":int(time.time()),"pool":POOL,"min_pos":MIN_POS,"board":board,"consensus":cons[:40],"weekly_movers":movers,
         "alltime":[{"rank":int(w["rank"]),"name":w.get("userName") or w["proxyWallet"][:8],"wallet":w["proxyWallet"],"pnl":w["pnl"]} for w in alltime]}
    os.makedirs("data",exist_ok=True); json.dump(out,open("data/data.json","w"),indent=1)
    print(f"wallets={len(board)} consensus={len(cons)} movers={len(movers)}")
if __name__=="__main__": main()
