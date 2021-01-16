<template>
  <div :class="$style.info">
    <button
      :disabled="fetchingActive"
      @click="update()"
      class="btn">
      <slot></slot>
    </button>
    <div v-if="!fetchingActive" class="flexCol">
      <span><strong>Last start time:</strong> {{ lastStartTime }}</span>
      <span><strong>Last finish time:</strong> {{ lastFinishTime }}</span>
    </div>
    <div v-else>
      <span>{{ message }}</span>
    </div>
  </div>
</template>

<script>
import utils from '../utils';

export default {
  data () {
    return {
      lastStartTime: null,
      lastFinishTime: null,
      refreshIntervalId: null,
    }
  },
  props: ['fetchingActive', 'message', 'updateUrl', 'refreshUrl'],
  methods: {
    update() {
      this.$emit('update-fetching-active', true);
      this.$emit('update-message', 'Update with Hackernews In Progress');
      this.axios
        .post(this.updateUrl)
        .catch((error) => {
          this.$emit('update-message', error.response.data.message);
        })
    },
    refresh() {
      this.axios
        .get(this.refreshUrl)
        .then((response) => {
          this.$emit('update-fetching-active', Boolean(response.data.running));
          this.lastStartTime = utils.toLocal(response.data.last_start_time);
          this.lastFinishTime = utils.toLocal(response.data.last_finish_time);
        });
    },
  },

  mounted () {
    this.refresh();
  },

  watch: {
    fetchingActive: function(newVal, oldVal) {
      if (newVal) {
       this.refreshIntervalId = setInterval(this.refresh, 5000);
      } else {
        clearInterval(this.refreshIntervalId);
        this.refresh();
      }
    }
  }
}
</script>

<style module lang="sass">
.info
  display: flex
  flex-direction: column
  justify-content: flex-start
  font-size: 8pt

</style>
