# moca
CS 410 group project: MOOC Course Assistant

## Setup
First, set up and import MOOC SQL databases:

```bash
echo "CREATE DATABASE textretrieval;" | mysql -u root
mysql -u root textretrieval < Text\ Retrieval\ and\ Search\ Engines\ \(textretrieval-001\)_SQL_anonymized_general.sql

echo "CREATE DATABASE textanalytics;" | mysql -u root
mysql -u root textanalytics < Text\ Mining\ and\ Analytics\ \(textanalytics-001\)_SQL_anonymized_general.sql
```

Next, set up Python app:

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
cp moca.cfg.sample moca.cfg
vim moca.cfg # Edit accordingly
```

Run the following to import topic distributions and lecture video topic coverage to SQL:

```bash
topic_data/import_topics.py
```

Finally, to run the app:

```bash
python app.py
```
