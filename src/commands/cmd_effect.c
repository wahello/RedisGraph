/*
 * Copyright Redis Ltd. 2018 - present
 * Licensed under your choice of the Redis Source Available License 2.0 (RSALv2) or
 * the Server Side Public License v1 (SSPLv1).
 */

#include "RG.h"
#include "../effects/effects.h"
#include "../graph/graphcontext.h"

// GRAPH.EFFECT command handler
int Graph_Effect
(
	RedisModuleCtx *ctx,       // redis module context
	RedisModuleString **argv,  // command arguments
	int argc                   // number of arguments
) {
	// GRAPH.EFFECT <key> <effects>
	if(argc != 3) {
		return RedisModule_WrongArity(ctx);
	}

	// get graph context
	GraphContext *gc = GraphContext_Retrieve(ctx, argv[1], false, true);
	ASSERT(gc != NULL);

	// get graph
	Graph *g = GraphContext_GetGraph(gc);

	//--------------------------------------------------------------------------
	// process effects
	//--------------------------------------------------------------------------

	size_t l = 0;  // effects buffer length
	const char *effects_buff = RedisModule_StringPtrLen(argv[2], &l);

	// lock graph for writing
	Graph_AcquireWriteLock(g);

	// apply effects
	Effects_Apply(gc, effects_buff, l);

	// release write lock
	Graph_ReleaseLock(g);

	// release GraphContext
	GraphContext_DecreaseRefCount(gc);

	return REDISMODULE_OK;
}

