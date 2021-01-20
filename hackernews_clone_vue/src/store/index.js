import { createStore, createLogger } from 'vuex'


export default createStore({
  state () {
    return {
      fetchingActive: false
    }
  },

  getters: {
    fetchingActive (state) {
      return state.fetchingActive;
    }
  },

  mutations: {
    setFetchingActive (state, val) {
      state.fetchingActive = val;
    },
  },

  actions: {
    setFetchingActive ({ commit, state }, val) {
      commit('setFetchingActive', val);
    },
  },
})
