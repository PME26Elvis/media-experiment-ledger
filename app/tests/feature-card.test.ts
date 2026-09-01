import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { describe, expect, it } from 'vitest'
import FeatureCard from '../src/renderer/components/FeatureCard.vue'

const HoverStub = defineComponent({
  setup(_props, { slots }) {
    return () => slots.default?.({ isHovering: false, props: { 'data-hover-contract': 'ready' } })
  },
})

const PassThrough = defineComponent({
  setup(_props, { slots }) { return () => slots.default?.() },
})

describe('FeatureCard', () => {
  it('renders semantic content through the Vuetify hover slot contract', () => {
    const wrapper = mount(FeatureCard, {
      props: { title: 'Atlas', subtitle: 'Evidence', icon: 'mdi-image' },
      global: {
        stubs: {
          VHover: HoverStub,
          VCard: PassThrough,
          VAvatar: PassThrough,
          VIcon: true,
        },
      },
    })
    expect(wrapper.text()).toContain('Atlas')
    expect(wrapper.text()).toContain('Evidence')
  })
})
