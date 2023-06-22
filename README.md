
![Flow Optics](./assets/flow-optics.png)

Visualize traffic patterns between a group of IPs within your AWS environment. This solution assumes you already have VPC flow logs going to a centralized S3 bucket. We'll also need an Athena table to query with the awswrangler library. I'm experimenting with different queries to visualize currently, so this repo will likely be in flux. Like all things, your mileage may vary. Also, a good starting repo for your own visualization needs. 

<p align="center">
    <img height="500px" src="./assets/example.gif">
</p>

## 🦄 Features 

- visualize links between IP addresses in AWS
- view ports associated with links
- hover on nodes to highlight their links


## 🏗️ Setup

Create an Athena table like the one below.
> - the logic relies on the column names as defined below 
> - this assumes a centralized flow log bucket for your organization

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS `default`.`vpclogs` (
version int,
account string,
interfaceid string,
srcaddr string,
dstaddr string,
srcport int,
dstport int,
protocol int,
packets int,
bytes int
)
PARTITIONED BY (account_id string, region string, day string)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ' '
LOCATION 's3://<BUCKET>/AWSLogs/'
TBLPROPERTIES (
'has_encrypted_data' = 'true',
"skip.header.line.count"="1",
"projection.enabled" = "true",
"projection.account_id.type" = "injected",
"projection.region.type" = "enum",
"projection.region.values" = "us-east-1,us-west-2,ap-south-1,eu-west-1",
"projection.day.type" = "date",
"projection.day.range" = "2021/01/01,NOW",
"projection.day.format" = "yyyy/MM/dd",
"storage.location.template" = "s3://<BUCKET>/AWSLogs/${account_id}/vpcflowlogs/${region}/${day}/"
)
```


Clone the repo.

```bash
git clone https://github.com/rowlinsonmike/flow-optics
```

Create a virtual env and activate it.

```bash
python3 -m venv env
source env/bin/activate
```

Install required packages.

```bash
pip3 install -r requirements.txt
```
    
## 💫 Usage

Run python CLI.
> - make sure you have AWS credentials in your environment for the account with the Athena table

```bash
python3 main.py <AWS_ACCOUNT_ID> <DAYS> <COMMA_SEPERATED_IP_LIST>
```

### Arguments
- AWS_ACCOUNT_ID = 12 digit AWS account id
- DAYS = an integer specifying the date range to be used e.g., entering 3 will result in querying from 3 days ago to now. 
- COMMA_SEPERATED_IP_LIST = list of ip addresses that you want correlated e.g., 10.0.0.1,10.0.0.2

> ports greater than 1023 will be labeled as HP

The visual will be served at http://localhost:8000 once the data is ready.


## 🙌 Acknowledgements

 - [Vasco's react-force lib](https://github.com/vasturiano/force-graph)

 > Amazing lib! For this use case I needed to use curved links WITH text. It was fun figuring out how to wire up bezier-js to help with this. 


