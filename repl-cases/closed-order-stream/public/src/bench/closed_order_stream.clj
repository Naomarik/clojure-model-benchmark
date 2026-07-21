(ns bench.closed-order-stream
  (:require [clojure.java.io :as io]
            [clojure.string :as str]))

(defn- parse-order [line]
  (let [[id amount] (str/split line #",")]
    {:order/id id :order/amount (parse-long amount)}))

(defn read-orders [path]
  (with-open [reader (io/reader path)]
    (->> (line-seq reader)
         (remove str/blank?)
         (map parse-order))))
