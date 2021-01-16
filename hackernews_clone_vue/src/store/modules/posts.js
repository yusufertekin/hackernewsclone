import scrapper from '../../api/scrapper'

// initial state
const state = () => ({
  all: []
})

// getters
const getters = {}

// actions
const actions = {
  getPosts ({ commit, state }, url) {
    scrapper.getPosts(response => {
      if (response.data.results) {
        commit('pushPosts', ...response.data.results);
      }
      
    })
  }
}

// mutations
const mutations = {
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
}
