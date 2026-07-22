import React from 'react';
import Subscription from './Subscription';

export default function SubscriptionPage({ apiFetch, user = {} }) {
  const orgId = user?.organization_id || user?.org_id || localStorage.getItem("organization_id") || localStorage.getItem("user_id") || "org_default";
  
  return <Subscription apiFetch={apiFetch} orgId={orgId} />;
}
