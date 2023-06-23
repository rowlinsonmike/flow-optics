import awswrangler as wr
import json
import typer
from datetime import datetime, timedelta
import http.server
import socketserver
import os
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from rich.table import Table
from ipaddress import IPv4Network, IPv4Address

console = Console()

def serve_site():
    #serve site
    class quietServer(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
    with socketserver.TCPServer(("", 8000), quietServer) as httpd:
        os.chdir('web')
        print("Serving visual at [green]http://localhost:8000[/green] , Control+C to exit.")
        httpd.serve_forever()

def filter_cidr(address,cidr=None):
    return lambda x: True if address == x else IPv4Address(x) in IPv4Network(cidr) if cidr else True


# cli 
app = typer.Typer()

@app.command()
def rejects(account:str, days: int, address: str, cidr: str = typer.Argument(None)):
    filter = filter_cidr(address,cidr)
    print("[green]Flow Optics[/green] checking for rejections!")
    current_date = datetime.now().date()
    days_ago = current_date - timedelta(days=days)
    date_string = days_ago.strftime("%Y/%m/%d")
    table = Table("Parameter", "Value")
    table.add_row("Account Id", account)
    table.add_row("Date Range", "{}-{}".format(date_string,current_date.strftime("%Y/%m/%d")))
    table.add_row("Address", address)
    console.print(table)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Querying Athena...", total=None)
        # run athena query
        dfs = wr.athena.read_sql_query(
            "SELECT * FROM default.vpclogs WHERE (account_id='{}' AND status = 'REJECT' AND day >= '{}' AND srcaddr in ('{}') )OR (account_id='{}' AND day >= '{}' AND dstaddr in ('{}'));".format(account,date_string,address,account,date_string,address,),
            database="default",
            chunksize=True  # Chunksize calculated automatically for ctas_approach.
        )
        progress.add_task(description="Compiling Data...", total=None)
        nodes = []
        curve_track = {}
        existing_lines = []
        lines = []

        for df in dfs:  # process dataframes
            df_nodes = list(set(list(df["srcaddr"].unique()) + list(df["dstaddr"].unique())))
            df_nodes = [x for x in df_nodes if filter(x)]
            nodes = list(set(nodes + df_nodes))
            for sa in list(df["srcaddr"].unique()):
                if not filter(sa):continue      
                for idx in df[df['srcaddr'] == sa].index:
                    sp = int(df['srcport'][idx]) if int(df['srcport'][idx]) < 1023 else 'HP'
                    da = str(df['dstaddr'][idx])
                    if not filter(da): continue
                    l = {"source": str(sa), "target": da, "label":sp}
                    if sp == 0: continue
                    if json.dumps(l) in existing_lines: continue
                    existing_lines.append(json.dumps(l))
                    curve_track[f"{sa}{da}"] = curve_track.get(f"{sa}{da}",0) + .3
                    lines.append({**l,"type":"reject","curvature":curve_track[f"{sa}{da}"]})
        data = {"nodes":[],"links":lines}
        for idx, s in enumerate(nodes):
            data['nodes'].append({ 'id': s, "group": idx + 1 })
        with open('./web/data.json','w') as f:
            json.dump(data,f)
    serve_site()

@app.command()
def inspect(account:str, days: int, address: str,cidr: str = typer.Argument(None)):
    filter = filter_cidr(address,cidr)
    print("[green]Flow Optics[/green] running inspection!")
    current_date = datetime.now().date()
    days_ago = current_date - timedelta(days=days)
    date_string = days_ago.strftime("%Y/%m/%d")
    table = Table("Parameter", "Value")
    table.add_row("Account Id", account)
    table.add_row("Date Range", "{}-{}".format(date_string,current_date.strftime("%Y/%m/%d")))
    table.add_row("Address", address)
    console.print(table)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Querying Athena...", total=None)
        # run athena query
        dfs = wr.athena.read_sql_query(
            "SELECT * FROM default.vpclogs WHERE (account_id='{}' AND day >= '{}' AND srcaddr in ('{}') )OR (account_id='{}' AND day >= '{}' AND dstaddr in ('{}'));".format(account,date_string,address,account,date_string,address,),
            database="default",
            chunksize=True  # Chunksize calculated automatically for ctas_approach.
        )
        progress.add_task(description="Compiling Data...", total=None)
        nodes = []
        curve_track = {}
        existing_lines = []
        lines = []

        for df in dfs:  # process dataframes
            df_nodes = list(set(list(df["srcaddr"].unique()) + list(df["dstaddr"].unique())))
            df_nodes = [x for x in df_nodes if filter(x)]
            nodes = list(set(nodes + df_nodes))
            for sa in list(df["srcaddr"].unique()):
                if not filter(sa):continue 
                for idx in df[df['srcaddr'] == sa].index:
                    sp = int(df['srcport'][idx]) if int(df['srcport'][idx]) < 1023 else 'HP'
                    da = str(df['dstaddr'][idx])
                    if not filter(da):continue 
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
    serve_site()

@app.command()
def correlate(account:str, days: int, addresses: str):
    print("[green]Flow Optics[/green] running correlation!")
    ips = addresses
    ips = ",".join(map(lambda x:f"'{x}'",ips.split(',')))
    current_date = datetime.now().date()
    two_days_ago = current_date - timedelta(days=days)
    date_string = two_days_ago.strftime("%Y/%m/%d")
    table = Table("Parameter", "Value")
    table.add_row("Account Id", account)
    table.add_row("Date Range", "{}-{}".format(date_string,current_date.strftime("%Y/%m/%d")))
    table.add_row("Addresses", ips)
    console.print(table)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Querying Athena...", total=None)
        # run athena query
        dfs = wr.athena.read_sql_query(
            "SELECT * FROM default.vpclogs WHERE account_id='{}' AND srcaddr in ({}) AND dstaddr in ({}) AND day >= '{}';".format(account,ips,ips,date_string),
            database="default",
            chunksize=True  # Chunksize calculated automatically for ctas_approach.
        )
        progress.add_task(description="Compiling Data...", total=None)
        nodes = []
        curve_track = {}
        existing_lines = []
        lines = []

        for df in dfs:  # process dataframes
            df_nodes = list(set(list(df["srcaddr"].unique()) + list(df["dstaddr"].unique())))
            nodes = list(set(nodes + df_nodes))
            for sa in list(df["srcaddr"].unique()):
                for idx in df[df['srcaddr'] == sa].index:
                    sp = int(df['srcport'][idx]) if int(df['srcport'][idx]) < 1023 else 'HP'
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
    serve_site()

@app.command()
def serve():
    serve_site()

if __name__ == "__main__":
    app()