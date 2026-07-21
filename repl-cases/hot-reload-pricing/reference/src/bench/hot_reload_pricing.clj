(ns bench.hot-reload-pricing
  (:require [clojure.edn :as edn]))

(def rules-path "resources/pricing.edn")
(defonce rules (atom (edn/read-string (slurp rules-path))))

(defn reload-rules! []
  (let [loaded (edn/read-string (slurp rules-path))]
    (reset! rules loaded)))

(defn price [cents customer-kind]
  (let [percent (get-in @rules [:discounts customer-kind] 0)]
    (- cents (quot (* cents percent) 100))))
