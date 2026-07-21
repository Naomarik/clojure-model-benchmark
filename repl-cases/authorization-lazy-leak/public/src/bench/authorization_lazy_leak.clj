(ns bench.authorization-lazy-leak)

(def ^:dynamic *tenant* nil)

(defn feed-page [rows page-size]
  (->> rows
       (take page-size)
       (filter #(= *tenant* (:design/tenant %)))
       (map #(select-keys % [:design/id :design/title]))))
