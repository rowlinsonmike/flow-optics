import awswrangler as wr
import json
import typer
from datetime import datetime, timedelta
import http.server
import socketserver
import os


# cli 
app = typer.Typer()

@app.command()
def query(account:str, days: int, addresses: str):
    ips = addresses
    ips = ",".join(map(lambda x:f"'{x}'",ips.split(',')))
    current_date = datetime.now().date()
    two_days_ago = current_date - timedelta(days=days)
    date_string = two_days_ago.strftime("%Y/%m/%d")
    # run athena query
    dfs = wr.athena.read_sql_query(
        "SELECT * FROM default.vpclogs WHERE account_id='{}' AND srcaddr in ({}) AND dstaddr in ({}) AND day >= '{}';".format(account,ips,ips,date_string),
        database="default",
        chunksize=True  # Chunksize calculated automatically for ctas_approach.
    )

    nodes = []
    curve_track = {}
    existing_lines = []
    lines = []

    for df in dfs:  # process dataframes
        df_nodes = list(set(list(df["srcaddr"].unique()) + list(df["dstaddr"].unique())))
        nodes = list(set(nodes + df_nodes))
        for sa in list(df["srcaddr"].unique()):
            for idx in df[df['srcaddr'] == sa].index:
                sp = int(df['srcport'][idx]) if int(df['srcport'][idx]) < 1023 else 'HIGHPORT'
                da = str(df['dstaddr'][idx])
                l = {"source": str(sa), "target": da, "label":sp}
                if sp == 0: continue
                if json.dumps(l) in existing_lines: continue
                existing_lines.append(json.dumps(l))
                curve_track[f"{sa}{da}"] = curve_track.get(f"{sa}{da}",0) + .3
                lines.append({**l,"curvature":curve_track[f"{sa}{da}"]})


    data = {"nodes":[],"links":lines}
    for idx, s in enumerate(nodes):
        data['nodes'].append({ 'id': s, "group": idx + 1 })
    with open('./web/data.json','w') as f:
        json.dump(data,f)
    #serve site
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), Handler) as httpd:
        os.chdir('web')
        print("Serving chart at http://localhost:8000. Control+C to exit.")
        httpd.serve_forever()

if __name__ == "__main__":
    app()