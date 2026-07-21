(ns bench.authorization-lazy-leak)

(def ^:dynamic *tenant* nil)

(defn feed-page [rows page-size]
  (let [tenant *tenant*]
    (->> rows
         (filter #(= tenant (:design/tenant %)))
         (take page-size)
         (mapv #(select-keys % [:design/id :design/title])))))
