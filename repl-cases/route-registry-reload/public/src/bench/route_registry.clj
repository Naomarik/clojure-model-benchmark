(ns bench.route-registry)

(defonce registry (atom {}))

(defmacro defroute [route-name path handler]
  `(swap! registry assoc ~route-name {:path ~path :handler ~handler}))

(defn dispatch [route-name request]
  (if-let [handler (get-in @registry [route-name :handler])]
    (handler request)
    {:status 404}))
