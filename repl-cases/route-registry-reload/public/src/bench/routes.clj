(ns bench.routes
  (:require [bench.route-handlers :as handlers]
            [bench.route-registry :refer [defroute]]))

(defroute :dashboard "/" handlers/dashboard)
