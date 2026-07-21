(ns bench.tenant-cache)

(defonce cache (atom {}))

(defn clear! [] (reset! cache {}))

(defn lookup [loader tenant revision product-id]
  (let [key [tenant revision product-id]]
    (if (contains? @cache key)
      (get @cache key)
      (let [entry (loader tenant product-id)]
        (swap! cache assoc key entry)
        entry))))
