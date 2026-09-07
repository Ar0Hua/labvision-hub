import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getLoginUserUsingGet } from '@/api/userController'

/**
 * 存储登录用户信息的状态
 */
export const useLoginUserStore = defineStore('loginUser', () => {
    const loginUser = ref<API.LoginUserVO>({
        userName: '未登录',
    })

    /**
     * 远程获取登录用户信息
     */
    async function fetchLoginUser() {
        const res = await getLoginUserUsingGet()
        if (res.data.code === 0 && res.data.data) {
            loginUser.value = res.data.data
        }
        //测试用户登录，3秒后自动登录
        /*         setTimeout(() => {
                    loginUser.value = {
                        id: 1,
                        username: '测试用户',
                    }
                }, 3000) */
    }

    /**
     * 设置登录用户
     * @param newLoginUser
     */
    function setLoginUser(newLoginUser: any) {
        loginUser.value = newLoginUser
    }

    // 返回
    return { loginUser, fetchLoginUser, setLoginUser }
})
