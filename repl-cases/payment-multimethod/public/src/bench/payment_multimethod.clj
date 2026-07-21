(ns bench.payment-multimethod)

(defmulti handle-payment (juxt :operation :provider))

(defmethod handle-payment :card [{:keys [amount]}]
  {:handled-by :card :amount amount})

(defmethod handle-payment :bank [{:keys [amount]}]
  {:handled-by :bank :amount amount})

(defmethod handle-payment :default [{:keys [operation provider]}]
  {:error :unsupported :operation operation :provider provider})
