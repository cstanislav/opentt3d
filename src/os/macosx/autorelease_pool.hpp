/* SPDX-License-Identifier: GPL-2.0-only */
/** @file autorelease_pool.hpp Scoped Cocoa ownership for C++ calls into native libraries. */
#ifndef AUTORELEASE_POOL_HPP
#define AUTORELEASE_POOL_HPP

class CocoaAutoreleasePool {
	void *pool;

public:
	CocoaAutoreleasePool();
	~CocoaAutoreleasePool();
	CocoaAutoreleasePool(const CocoaAutoreleasePool &) = delete;
	CocoaAutoreleasePool &operator=(const CocoaAutoreleasePool &) = delete;
};

#endif /* AUTORELEASE_POOL_HPP */
