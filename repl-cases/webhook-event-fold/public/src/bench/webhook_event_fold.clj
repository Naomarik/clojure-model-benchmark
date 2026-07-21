(ns bench.webhook-event-fold)

(def initial-state
  {:status :new :last-seq -1 :seen #{} :effects []})

(defn apply-event [state {:keys [id sequence type]}]
  (if (contains? (:seen state) id)
    state
    (-> state
        (update :seen conj id)
        (assoc :last-seq sequence)
        (cond-> (= type :subscription/created) (assoc :status :active)
                (= type :subscription/canceled) (assoc :status :canceled)
                (= type :invoice/paid) (update :effects conj [:send-receipt id])))))

(defn fold-events [state events]
  (reduce apply-event state events))
