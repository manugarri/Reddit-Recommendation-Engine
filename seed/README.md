
#Seed folder. 

**Used to  generate the dataset and calculate the similarity**

###How to generate the dataset

1. Run `subreddits.py` to get list of subreddits with the number of redditors

2. select the top N subreddits (I chose all subreddits with more than above 10,000 redditors)

3. Save the subreddits to analyze on `subs.json`

4. Set up your database. In my case I used a Postgres database.

5. Get the redditor - comments dataset by running `redditors.py`

5. Let it run! The longest you let it run the bigger your dataset will be. In my case I waited for more than a week, until I had around 1M rows.

6. Create the similarity table 

```
CREATE TABLE similarity_comments IF NOT EXISTS (
       sub1 varchar(20),
       sub2 varchar(1000),
       similarity float);
```
6. Compute the Subreddit similarity. Initially I used python to compute the similarity between subs. You can run it with `similarity.py`.

   However, because computing the similarities takes a long time, I rewrote the similarity calculation script in Go. You can run it with `go run similarity.go`

7. It will take some time (on my machine it took about 3 full days). But at the end you will have a table with the similarity between each sub.

Alternativaly, you can just download the file similarity.csv and populate your table with it :). 
