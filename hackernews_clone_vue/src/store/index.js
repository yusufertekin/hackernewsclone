import { createStore, createLogger } from 'vuex'
import axios from 'axios';

const debug = process.env.NODE_ENV === 'dev'
const apiHostUrl = __API_HOST_URL__;

export default createStore({
  state () {
    return {
      posts: [],
      url: `${apiHostUrl}posts/`,
      nextUrl: null,
      intervalId: null,
      message: null,
      fetchingActive: false,
    }
  },

  mutations: {
    pushPosts (state, posts) {
      state.posts.push(posts)
    },
    setPosts (state, posts) {
      state.posts = posts
    },
    setNextUrl (state, url) {
      state.nextUrl = url
    },
    setIntervalId (state, intervalId) {
      state.intervalId = intervalId
    },
    clearIntervalId (state) {
      state.intervalId = null
    }
  },

  actions: {
    getPosts ({ commit, dispatch }, url) {
      axios
        .get(url)
        .then((response) => {
          if (response.data.results) {
            commit('pushPosts', ...response.data.results);
            commit('setNextUrl', response.data.next);
            commit('clearInterval');
            dispatch('getLastRunAt');
          }
        })
    },
    getLastRunAt ({ commit, state }) {
      axios
        .get(`${apiHostUrl}get-last-run-at/`)
        .then((response) => {
          commit('setFetchingActive', Boolean(response.data.running));
          state.lastStartTime = toLocal(response.data.last_start_time);
          this.taskInfo.lastFinishTime = toLocal(response.data.last_finish_time);
        });
    }
  },
  strict: debug,
  plugins: debug ? [createLogger()] : []
})
