package main

import (
	"models"
	"net/http"
	"utils"

	"github.com/codegangsta/negroni"
	"github.com/coopernurse/gorp"
	"github.com/gorilla/sessions"
	"github.com/joho/godotenv"
	"github.com/julienschmidt/httprouter"
)

var (
	sessionStore *sessions.CookieStore
	dbmap        *gorp.DbMap
)

func main() {
	err := godotenv.Load()
	utils.CheckErr(err, "Error loading Environment Variables")

	dbmap = models.InitDb()
	cookieSecret := "a"
	sessionStore = sessions.NewCookieStore([]byte(cookieSecret))

	r := setupRoutes()

	n := negroni.New()
	n.Use(negroni.NewLogger())
	n.Use(negroni.NewRecovery())
	n.Use(negroni.NewStatic(http.Dir("public")))
	n.UseHandler(r)
	n.Run(":4000")
}

type AppContext struct {
	Params  httprouter.Params
	Session *sessions.Session
	DbMap   *gorp.DbMap
}

type AccessToken struct {
	AccessToken string `json:"access_token"`
	token_type  string
	expires_in  int
	scope       string
}

type HttpApiFunc func(c *AppContext, w http.ResponseWriter, r *http.Request)

func newAppContext(r *http.Request) *AppContext {
	session, _ := sessionStore.Get(r, "developers")
	return &AppContext{
		Params:  nil,
		Session: session,
		DbMap:   dbmap,
	}
}

func setupRoutes() *httprouter.Router {
	router := httprouter.New()
	router.POST("/results", makeHandler(resultsHandler))
	router.GET("/authorize_callback", makeHandler(callbackHandler))
	router.GET("/auth", makeHandler(oauthHandler))
	router.GET("/", makeHandler(indexHandler))
	return router
}

func jsonize(fct HttpApiFunc) HttpApiFunc {
	return func(c *AppContext, w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fct(c, w, r)
	}
}

func makeHandler(fct HttpApiFunc) httprouter.Handle {
	return func(w http.ResponseWriter, r *http.Request, params httprouter.Params) {
		c := newAppContext(r)
		c.Params = params
		fct(c, w, r)
	}
}
