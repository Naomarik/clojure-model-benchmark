(ns grader
  (:require [bench.payment-multimethod :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(deftest dispatches-by-operation-and-provider
  (is (= {:handled-by :card :operation :charge :amount 40}
         (sut/handle-payment {:operation :charge :provider :card :amount 40})))
  (is (= {:handled-by :card :operation :refund :amount 12}
         (sut/handle-payment {:operation :refund :provider :card :amount 12})))
  (is (= {:handled-by :bank :operation :charge :amount 90}
         (sut/handle-payment {:operation :charge :provider :bank :amount 90})))
  (is (= {:error :unsupported :operation :refund :provider :bank}
         (sut/handle-payment {:operation :refund :provider :bank :amount 9})))
  (is (= #{[:charge :card] [:refund :card] [:charge :bank] :default}
         (set (keys (methods sut/handle-payment))))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
