(ns bench.transducer-completion)

(defn partition-until [pred]
  (fn [rf]
    (let [buffer (volatile! [])]
      (fn
        ([] (rf))
        ([result] (rf result))
        ([result input]
         (vswap! buffer conj input)
         (if (pred input)
           (let [batch @buffer]
             (vreset! buffer [])
             (rf result batch))
           result))))))
