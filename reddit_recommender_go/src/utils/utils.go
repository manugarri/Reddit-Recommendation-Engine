package utils

import (
	"encoding/json"
	"log"
)

func CheckErr(err error, msg string) {
	if err != nil {
		log.Fatalln(msg, err)
		//panic(err)
	}
}

type Response map[string]interface{}

func (r Response) String() (s string) {
	b, err := json.Marshal(r)
	if err != nil {
		s = ""
		return
	}
	s = string(b)
	return
}

func MapToJSON(m interface{}) []byte {
	j, err := json.Marshal(m)
	if err != nil {
		log.Fatal("ERROR MapToJson", err)
	}

	return j
}

func StringInSlice(a string, list []string) bool {
	for _, b := range list {
		if b == a {
			return true
		}
	}
	return false
}

func Concat(old1, old2 []string) []string {
	newslice := make([]string, len(old1)+len(old2))
	copy(newslice, old1)

	for _, e := range old2 {
		if StringInSlice(e, newslice) == false {
			newslice = append(newslice, e)
		}
	}
	//copy(newslice[len(old1):], old2)
	//newslice = removeDuplicates(newslice)
	return newslice
}

func removeDuplicates(a []string) []string {
	result := []string{}
	seen := map[string]string{}
	for _, val := range a {
		if _, ok := seen[val]; !ok {
			result = append(result, val)
			seen[val] = val
		}
	}
	return result
}
