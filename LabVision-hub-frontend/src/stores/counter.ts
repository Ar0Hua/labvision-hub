import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

//一个状态就储存一类要共享的数据（存一类常量）
export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)

  //定义状态的初始值
  //定义变量的计算逻辑
  const doubleCount = computed(() => count.value * 2)

  //定义怎么更改状态的方法
  function increment() {
    count.value++
  }

  return { count, doubleCount, increment }
})


