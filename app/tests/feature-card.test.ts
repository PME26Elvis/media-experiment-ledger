import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import FeatureCard from '../src/renderer/components/FeatureCard.vue'
describe('FeatureCard',()=>{ it('renders semantic content',()=>{ const wrapper=mount(FeatureCard,{props:{title:'Atlas',subtitle:'Evidence',icon:'mdi-image'}}); expect(wrapper.text()).toContain('Atlas'); expect(wrapper.text()).toContain('Evidence') }) })
