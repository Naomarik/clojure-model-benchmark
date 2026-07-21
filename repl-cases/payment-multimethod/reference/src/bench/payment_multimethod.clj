(ns bench.payment-multimethod)

(defmulti handle-payment (juxt :operation :provider))

(defmethod handle-payment [:charge :card] [{:keys [amount]}]
  {:handled-by :card :operation :charge :amount amount})

(defmethod handle-payment [:refund :card] [{:keys [amount]}]
  {:handled-by :card :operation :refund :amount amount})

(defmethod handle-payment [:charge :bank] [{:keys [amount]}]
  {:handled-by :bank :operation :charge :amount amount})

(defmethod handle-payment :default [{:keys [operation provider]}]
  {:error :unsupported :operation operation :provider provider})
