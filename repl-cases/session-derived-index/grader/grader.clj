(ns grader
  (:require [bench.session-derived-index :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(def s1 {:session/id "s1" :session/user 7 :session/token "a"})
(def s2 {:session/id "s2" :session/user 7 :session/token "b"})
(def s3 {:session/id "s3" :session/user 9 :session/token "c"})

(deftest index-tracks-primary-state
  (sut/reset-state!)
  (sut/put-session! s2)
  (sut/put-session! s1)
  (sut/put-session! s3)
  (is (= [s1 s2] (sut/sessions-for 7)))
  (is (= [s3] (sut/sessions-for 9)))
  (sut/delete-session! "s1")
  (is (= [s2] (sut/sessions-for 7)))
  (sut/rebuild-index!)
  (sut/rebuild-index!)
  (is (= {7 [s2] 9 [s3]} @sut/by-user)))

(deftest rebuild-removes-stale-users
  (sut/reset-state!)
  (reset! sut/by-user {99 [{:session/id "old" :session/user 99}]})
  (sut/rebuild-index!)
  (is (= {} @sut/by-user)))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
