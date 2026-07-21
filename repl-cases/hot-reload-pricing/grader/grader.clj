(ns grader
  (:require [bench.hot-reload-pricing :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(deftest refreshes-rules-safely
  (let [file (java.io.File/createTempFile "pricing" ".edn")
        path (.getPath file)]
    (spit file "{:discounts {:vip 25}}")
    (with-redefs [sut/rules-path path]
      (reset! sut/rules {:discounts {:vip 10}})
      (is (= {:discounts {:vip 25}} (sut/reload-rules!)))
      (is (= 7500 (sut/price 10000 :vip)))
      (spit file "{")
      (is (thrown? Exception (sut/reload-rules!)))
      (is (= 7500 (sut/price 10000 :vip))))
    (.delete file)))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
