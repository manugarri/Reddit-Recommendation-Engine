package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"models"
	"net/http"
	"net/url"
	"os"
	"strings"
	"utils"
)

func getApi(token string, url string) []byte {
	client := &http.Client{}
	r, _ := http.NewRequest("GET", url, nil)
	r.Header.Set("Authorization", "bearer "+token)
	r.Header.Set("Content-Type", "json")
	resp, err := client.Do(r)

	utils.CheckErr(err, fmt.Sprint("ERROR GETTING URL REQUEST: %s", url))
	data, _ := ioutil.ReadAll(resp.Body)
	return data
}

func processReddit(authCode string) (int, []string) {
	accessToken := getRedditAccessToken(authCode)
	if accessToken != "error" {
		redditor := getRedditorName(accessToken)
		subscribedSubs := getSubscriptions(accessToken, redditor)
		go RedditorInsertFlow(accessToken, redditor, subscribedSubs)
		recommendedSubs := computeRedditorSimilarity(subscribedSubs)
		log.Println("REDDITOR: ", redditor, "RECOMMENDATIONS: ", recommendedSubs)
		return len(subscribedSubs), recommendedSubs
	} else {
		return 0, []string{}
	}
}

//We get the comments subs to recompute similarity
func RedditorInsertFlow(accessToken string, redditor string, subscribedSubs []string) {
	commentedSubs := getComments(accessToken, redditor)
	insertRedditorComments(redditor, commentedSubs)
	insertRedditorSubscriptions(redditor, subscribedSubs)
}

func insertRedditorComments(redditor string, subs []string) {
	var redditorSubsComments []interface{}
	for _, s := range subs {
		rs := &models.RedditorSubsComments{redditor, s}
		redditorSubsComments = append(redditorSubsComments, rs)
	}
	deleteQuery := "DELETE FROM redditors_comments WHERE redditor='" + redditor + "';"
	_, err := dbmap.Exec(deleteQuery)
	utils.CheckErr(err, "ERROR DELETING USER FROM redditors_comments")
	err = dbmap.Insert(redditorSubsComments...)
	utils.CheckErr(err, "ERROR INSERTING ON COMMENTS TABLE")
}

func insertRedditorSubscriptions(redditor string, subs []string) {
	var redditorSubsSubscriptions []interface{}
	for _, s := range subs {
		rs := &models.RedditorSubsSubscriptions{redditor, s}
		redditorSubsSubscriptions = append(redditorSubsSubscriptions, rs)
	}
	deleteQuery := "DELETE FROM redditors_subscriptions WHERE redditor='" + redditor + "';"
	_, err := dbmap.Exec(deleteQuery)
	utils.CheckErr(err, "ERROR DELETING USER FROM redditors_subscriptions")
	err = dbmap.Insert(redditorSubsSubscriptions...)
	utils.CheckErr(err, "ERROR INSERTING ON SUBSCRIPTIONS TABLE")
}

func getRedditAccessToken(authCode string) string {
	accessTokenUrl := "https://ssl.reddit.com/api/v1/access_token"
	client := &http.Client{}
	data := url.Values{"code": {authCode}, "grant_type": {"authorization_code"},
		"redirect_uri": {os.Getenv("REDDIT_REDIRECT_URI")}}
	r, _ := http.NewRequest("POST", accessTokenUrl, strings.NewReader(data.Encode()))
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	r.SetBasicAuth(os.Getenv("REDDIT_CLIENT_ID"), os.Getenv("REDDIT_CLIENT_SECRET"))
	resp, err := client.Do(r)
	utils.CheckErr(err, "ERROR ON ACCESS TOKEN REQUEST")

	body, _ := ioutil.ReadAll(resp.Body)
	var t AccessToken
	//decoder := json.NewDecoder(resp.Body)
	//err = decoder.Decode(&t)
	err = json.Unmarshal(body, &t)
	utils.CheckErr(err, "ERROR DECODING JSON DATA")
	if err != nil || len(t.AccessToken) == 0 {
		log.Println("ERROR ACCESS TOKEN")
		return "error"
	} else {
		return t.AccessToken
	}
}

type RedditorName struct {
	Name  string `json:"name"`
	other json.RawMessage
}

func getRedditorName(token string) string {
	var n RedditorName
	nameUrl := "https://oauth.reddit.com/api/v1/me"
	data := getApi(token, nameUrl)
	err := json.Unmarshal(data, &n)
	utils.CheckErr(err, "ERROR DECODING JSON DATA")
	return n.Name
}

type CommentsData struct {
	_    json.RawMessage
	Data struct {
		Children []struct {
			Data struct {
				Subreddit string `json:"subreddit"`
				_         json.RawMessage
			}
		} `json:"children"`
		After string `json:"after"`
	} `json:"data"`
}

func getComments(token string, redditor string) []string {
	var comments CommentsData
	var commentedSubreddits []string
	after := ""
	for {
		commentsUrl := fmt.Sprintf("https://oauth.reddit.com/user/%s/comments?limit=100&after=%s", redditor, after)
		data := getApi(token, commentsUrl)
		err := json.Unmarshal(data, &comments)
		utils.CheckErr(err, "ERROR DECODING JSON DATA")
		children := comments.Data.Children

		for _, s := range children {
			if utils.StringInSlice(s.Data.Subreddit, commentedSubreddits) == false {
				commentedSubreddits = append(commentedSubreddits, s.Data.Subreddit)
			}
		}

		after = comments.Data.After
		if len(children) < 100 {
			break
		}
	}
	return commentedSubreddits
}

type SubscriptionData struct {
	_    json.RawMessage
	Data struct {
		Children []struct {
			Data struct {
				Subreddit string `json:"display_name"`
				_         json.RawMessage
			}
		} `json:"children"`
		After string `json:"after"`
	} `json:"data"`
}

func getSubscriptions(token string, redditor string) []string {
	var subscriptions SubscriptionData
	var subscribedSubreddits []string
	subscriptionUrl := "https://oauth.reddit.com/subreddits/mine/subscriber"

	data := getApi(token, subscriptionUrl)
	err := json.Unmarshal(data, &subscriptions)
	utils.CheckErr(err, "ERROR DECODING JSON DATA")
	children := subscriptions.Data.Children

	for _, s := range children {
		if utils.StringInSlice(s.Data.Subreddit, subscribedSubreddits) == false {
			subscribedSubreddits = append(subscribedSubreddits, s.Data.Subreddit)
		}
	}
	return subscribedSubreddits
}

type SubSim struct {
	Sub        string  `db:"sub"`
	Similarity float64 `db:"sim"`
}

func computeRedditorSimilarity(subs []string) []string {
	var simSubs []SubSim
	var recommendedSubs []string
	rawQuery := "SELECT sub1 AS sub, COALESCE(sim1,0) + COALESCE(sim2,0) AS sim " +
		"FROM ( SELECT * FROM (SELECT sub1, SUM(similarity) AS sim1 " +
		"FROM similarity_comments WHERE sub1 IN (%s) OR sub2 IN (%s) " +
		"GROUP BY sub1 ) AS s1   INNER JOIN ( SELECT sub2, SUM(similarity) " +
		"AS sim2 FROM similarity_comments WHERE sub1 IN (%s) OR sub2 IN (%s) " +
		"GROUP BY sub2) AS s2  ON (s1.sub1=s2.sub2)) AS result  WHERE sub1 " +
		"NOT IN (%s) ORDER BY SIM DESC LIMIT 20;"

	for i, _ := range subs {
		subs[i] = "'" + subs[i] + "'"
	}
	subsString := strings.Join(subs, ",")

	query := fmt.Sprintf(rawQuery, subsString, subsString, subsString, subsString, subsString)

	_, err := dbmap.Select(&simSubs, query)
	utils.CheckErr(err, "RECOMMENDATION SELECT failed")

	for _, subSim := range simSubs {
		recommendedSubs = append(recommendedSubs, subSim.Sub)
	}
	return recommendedSubs
}
