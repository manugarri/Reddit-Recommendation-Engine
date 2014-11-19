package models

import (
	"database/sql"
	"log"
	"os"
	"sync"

	"utils"

	"github.com/coopernurse/gorp"
	_ "github.com/lib/pq"
)

func ComputeSubsSimilarity() {
	dbmap := InitDb()
	var subs []string
	n_threads := 200 //This will depend on your machine
	_, err := dbmap.Select(&subs, "select distinct(sub) from redditors_comments order by sub asc")
	utils.CheckErr(err, "Error selecting redditors")
	calculateSimilarity(subs, n_threads)
}
func createSplitSlice(s []string, n int) [][]string {
	lenSlice := int(len(s) / n)
	splitSlice := make([][]string, n)
	i := 0
	for _, e := range s {
		if len(splitSlice) > lenSlice {
			i = i + 1
		}
		splitSlice[i] = append(splitSlice[i], e)

	}
	return splitSlice
}

type RedditorSubsComments struct {
	Redditor string `db:"redditor"`
	Sub      string `db:"sub"`
}

type RedditorSubsSubscriptions struct {
	Redditor string `db:"redditor"`
	Sub      string `db:"sub"`
}

type SimilarityComments struct {
	Sub1       string  `db:"sub1"`
	Sub2       string  `db:"sub2"`
	Similarity float64 `db:"similarity"`
}

func InitDb() *gorp.DbMap {

	user := "DB_USER"
	password := "DB_USER"
	host := "DB_HOST"
	port := "DB_PORT"
	dbname := "DB_NAME"

	dbString := "host=" + host +
		" port=" + port +
		" user=" + user +
		" password=" + password +
		" dbname=" + dbname
	log.Println("\nSetting new Postgres Connection", dbString)
	db, err := sql.Open("postgres", dbString)
	dbmap := &gorp.DbMap{Db: db, Dialect: gorp.PostgresDialect{}}

	utils.CheckErr(err, "sql.Open failed")
	dbmap.TraceOn("[gorp]", log.New(os.Stdout, "reddit:", log.Lmicroseconds))
	dbmap.AddTableWithName(RedditorSubsComments{}, "redditors_comments")
	dbmap.AddTableWithName(SimilarityComments{}, "similarity_comments")
	return dbmap
}

func calculateSimilarity(subs []string, n_operators int) {
	lenSlice := int(len(subs) / n_operators)
	var start int
	var end int
	var wg sync.WaitGroup
	for op := 0; op < n_operators; op++ {
		start = op * lenSlice
		end = (op + 1) * lenSlice
		wg.Add(1)
		go calculateSliceSimilarity(subs, start, end, &wg)
	}
	wg.Wait()
}
func calculateSliceSimilarity(subs []string, start int, end int, wg *sync.WaitGroup) {
	/* sort subs
		n processors
		each procesor process lenSplice = len(subs) / n_processors
		each processor process subs[i*lenSplice:(i+1)*lenSplice]
	        for each sub:
		    calculate similarity of that sub and those after it
	*/
	dbmap := InitDb()
	defer dbmap.Db.Close()
	lenSubs := len(subs)
	for i := start; i < end; i++ {
		for j := i + 1; j < lenSubs; j++ {
			calculateSubsSimilarity(subs[i], subs[j], dbmap)
		}
	}
	wg.Done()
}

func calculateSubsSimilarity(sub1 string, sub2 string, dbmap *gorp.DbMap) {
	var count_union []int
	var count_intersection []int
	var union int
	var intersection int
	var similarity float64
	query := "Select count(distinct(redditor)) from redditors_comments where sub ='" + sub1 +
		"' or sub ='" + sub2 + "';"
	_, err := dbmap.Select(&count_intersection, query)
	utils.CheckErr(err, "Error on subsimilarity union")
	intersection = count_intersection[0]

	query = "select count(distinct(redditor)) from redditors_comments where sub='" +
		sub1 + "' and redditor in (select distinct(redditor) from redditors_comments where sub='" + sub2 + "');"

	_, err = dbmap.Select(&count_union, query)
	utils.CheckErr(err, "Error on subsimilarity intersection")
	union = count_union[0]
	similarity = float64(union) / float64(intersection)
	s := &SimilarityComments{sub1, sub2, similarity}
	err = dbmap.Insert(s)
	utils.CheckErr(err, "Error inserting similarity")
}
