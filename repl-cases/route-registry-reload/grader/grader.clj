(ns grader
  (:require [bench.route-handlers :as handlers]
            [bench.route-registry :as registry]
            [bench.routes]
            [clojure.test :refer [deftest is run-tests]]))

(deftest registry-follows-var-roots
  (is (= {:status 200 :body "dashboard-v1"}
         (registry/dispatch :dashboard {})))
  (is (var? (get-in @registry/registry [:dashboard :handler])))
  (alter-var-root #'handlers/dashboard
                  (constantly (fn [_] {:status 200 :body "dashboard-v2"})))
  (is (= {:status 200 :body "dashboard-v2"}
         (registry/dispatch :dashboard {})))
  (is (= {:status 404} (registry/dispatch :missing {})))
  (is (= #{:dashboard} (set (keys @registry/registry)))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
