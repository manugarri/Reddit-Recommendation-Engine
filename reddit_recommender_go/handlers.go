package main

import (
	"fmt"
	"net/http"
	"net/url"
	"os"
	"utils"

	"github.com/gorilla/sessions"
)

func indexHandler(c *AppContext, w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "public/index.html")
}

func oauthHandler(c *AppContext, w http.ResponseWriter, r *http.Request) {
	redirectUri := url.QueryEscape(os.Getenv("REDDIT_REDIRECT_URI"))
	redditClientId := os.Getenv("REDDIT_CLIENT_ID")
	stateString := os.Getenv("REDDIT_STATE")
	oauthUrl := "https://ssl.reddit.com/api/v1/authorize?client_id=%s&response_type=code&state=%s&redirect_uri=%s&duration=temporary&scope=history,mysubreddits,identity"
	oauthUrl = fmt.Sprintf(oauthUrl, redditClientId, stateString, redirectUri)
	http.Redirect(w, r, oauthUrl, http.StatusSeeOther)
}

func callbackHandler(c *AppContext, w http.ResponseWriter, r *http.Request) {
	queryParams := r.URL.Query()
	if queryParams["state"][0] == os.Getenv("REDDIT_STATE") {
		authCode := queryParams["code"][0]
		session, _ := sessionStore.Get(r, "session-name")
		session.Values["done"] = false
		session.Values["authCode"] = authCode
		session.Save(r, w)

		http.ServeFile(w, r, "public/results.html")
	} else {
		http.ServeFile(w, r, "public/index.html")
	}
}

type Result struct {
	NumberSubs int      `json:"nsubs"`
	Subs       []string `json:"subs"`
}

func resultsHandler(c *AppContext, w http.ResponseWriter, r *http.Request) {
	authCode := c.Session.Values["authCode"].(string)
	nsubs, recommendedSubs := processReddit(authCode)
	res := &Result{nsubs, recommendedSubs}
	js := utils.MapToJSON(res)
	c.Session.Options = &sessions.Options{MaxAge: -1}
	c.Session.Save(r, w)
	w.Header().Set("Content-Type", "application/json")
	w.Write(js)
}
