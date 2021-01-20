<template>
  <div :class="$style.info">
    <button
      :disabled="fetchingActive"
      @click="update()"
      class="btn">
      <slot></slot>
    </button>
    <div v-if="fetchingStatus !== 'Active'" class="flexCol">
      <div :class="$style.row">
        <strong>Last Run At:</strong>
        <span>{{ lastRunAt }}</span>
      </div>
      <div :class="$style.row">
        <strong>Last Run Finish At:</strong>
        <span>{{ lastRunFinishAt }}</span>
      </div>
    </div>
    <div :class="$style.row">
      <strong>Status:</strong>
      <span>{{ fetchingStatus }}</span>
    </div>
  </div>
</template>

<script>
import utils from '../utils';

export default {
  data () {
    return {
      lastRunAt: null,
      lastRunFinishAt: null,
      refreshIntervalId: null,
      fetchingStatus: null,
    }
  },

  props: ['updateUrl', 'refreshUrl'],

  computed: {
    fetchingActive() {
      return this.$store.getters.fetchingActive;
    }
  },

  methods: {
    update() {
      this.fetchingStatus = 'Active'
      this.$store.dispatch('setFetchingActive', true);
      this.axios.post(this.updateUrl)
    },
    refresh() {
      this.axios
        .get(this.refreshUrl)
        .then((response) => {
          this.fetchingStatus = response.data.status;
          this.$store.dispatch('setFetchingActive', this.fetchingStatus === 'Active');
          this.lastRunAt = utils.toLocal(response.data.last_run_at);
          this.lastRunFinishAt = utils.toLocal(response.data.last_run_finish_at);
        });
    },
  },

  mounted () {
    this.refresh();
  },

  watch: {
    fetchingStatus: function(newVal, oldVal) {
      if (newVal === 'Active') {
       this.refreshIntervalId = setInterval(this.refresh, 5000);
      } else if (oldVal !== newVal) {
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

.row
  display: grid
  grid-template-columns: 1fr 1fr
  grid-template-rows: 1fr
  margin-top: 2px

</style>
