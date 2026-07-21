(ns bench.session-derived-index)

(defonce sessions (atom {}))
(defonce by-user (atom {}))

(defn reset-state! []
  (reset! sessions {})
  (reset! by-user {}))

(defn rebuild-index! []
  (reset! by-user
          (update-vals (group-by :session/user (vals @sessions))
                       #(vec (sort-by :session/id %)))))

(defn put-session! [session]
  (swap! sessions assoc (:session/id session) session)
  (rebuild-index!)
  session)

(defn delete-session! [session-id]
  (swap! sessions dissoc session-id)
  (rebuild-index!)
  nil)

(defn sessions-for [user-id]
  (vec (get @by-user user-id [])))
