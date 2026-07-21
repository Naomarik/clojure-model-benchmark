(ns bench.tenant-cache)

(defonce cache (atom {}))

(defn clear! [] (reset! cache {}))

(defn lookup [loader tenant revision product-id]
  (if-let [entry (get @cache product-id)]
    entry
    (let [entry (loader tenant product-id)]
      (swap! cache assoc product-id entry)
      entry)))
