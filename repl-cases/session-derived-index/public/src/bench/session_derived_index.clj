(ns bench.session-derived-index)

(defonce sessions (atom {}))
(defonce by-user (atom {}))

(defn reset-state! []
  (reset! sessions {})
  (reset! by-user {}))

(defn put-session! [session]
  (swap! sessions assoc (:session/id session) session)
  session)

(defn delete-session! [session-id]
  (swap! sessions dissoc session-id)
  nil)

(defn rebuild-index! []
  (swap! by-user merge (group-by :session/user (vals @sessions))))

(defn sessions-for [user-id]
  (vec (get @by-user user-id [])))
