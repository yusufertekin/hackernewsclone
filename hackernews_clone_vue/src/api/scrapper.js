import axios from 'axios';

export default {
  getPosts (url) {
    return axios.get(url);
  },
}
