const defaults = {
    isIdle: false,
    idledFor: 0
}

const state = Object.assign({}, defaults);
const getters = {
    isIdle: (state: any) => state.isIdle,
    idledFor: (state: any) => state.idledFor
}

const mutations = {
    setIsIdle(state: any, value: boolean) {
        state.isIdle = value
    },
    setIdledFor(state: any, value: number) {
        state.idledFor = value
    }
}


export default {
    state,
    mutations,
    getters,
}